/* ══════════════════════════════════════════
   GarageOS — Suggestion / Autocomplete
   suggestion.js
   ══════════════════════════════════════════ */

/**
 * Reusable autocomplete/suggestion module.
 *
 * Usage:
 *   initSuggestion(inputElement, '/suggestions/inventory/', {
 *     onSelect: (word) => { ... },   // optional callback
 *     minChars: 3,                    // min chars before fetching (default 3)
 *     debounceMs: 300,                // debounce delay (default 300)
 *     paramName: 'q',                 // query param name (default 'q')
 *   });
 */

(function () {
    'use strict';

    /* ── Helpers ── */
    function debounce(fn, ms) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), ms);
        };
    }

    /* ── Core ── */
    function initSuggestion(input, url, opts = {}) {
        if (!input || !url) {
            console.error('initSuggestion: input element and url are required');
            return;
        }

        const minChars = opts.minChars || 3;
        const debounceMs = opts.debounceMs || 300;
        const paramName = opts.paramName || 'q';
        const onSelect = opts.onSelect || null;

        let controller = null;   // AbortController for in-flight request
        let activeIndex = -1;     // keyboard navigation index
        let items = [];     // current suggestion DOM items

        /* ── Word extraction helpers ── */
        function getLastWord(value) {
            const words = value.split(/\s+/);
            return words[words.length - 1] || '';
        }

        function replaceLastWord(value, replacement) {
            const words = value.split(/\s+/);
            words[words.length - 1] = replacement;
            return words.join(' ');
        }

        /* ── Build DOM ── */
        // Wrap the parent .search-box so the dropdown is positioned relative to it
        const wrap = input.closest('.search-box') || input.parentElement;
        wrap.style.position = 'relative';

        const dropdown = document.createElement('div');
        dropdown.className = 'suggestion-dropdown';
        dropdown.setAttribute('role', 'listbox');
        dropdown.setAttribute('aria-label', 'Suggestions');
        wrap.appendChild(dropdown);

        /* ── Fetch suggestions ── */
        async function fetchSuggestions(query) {
            // Abort previous request
            if (controller) controller.abort();
            controller = new AbortController();

            try {
                const res = await fetch(`${url}?${paramName}=${encodeURIComponent(query)}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    signal: controller.signal,
                });

                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const json = await res.json();

                if (json.success && Array.isArray(json.data)) {
                    renderDropdown(json.data, query);
                } else {
                    hideDropdown();
                }
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.warn('Suggestion fetch failed:', err);
                    hideDropdown();
                }
            }
        }

        /* ── Render ── */
        function renderDropdown(words, query) {
            if (!words.length) {
                hideDropdown();
                return;
            }

            activeIndex = -1;
            dropdown.innerHTML = '';

            words.forEach((word, idx) => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.setAttribute('role', 'option');
                item.dataset.index = idx;

                // Highlight matching substring
                item.innerHTML = highlightMatch(word, query);

                item.addEventListener('mousedown', (e) => {
                    e.preventDefault(); // prevent input blur
                    selectItem(word);
                });

                item.addEventListener('mouseenter', () => {
                    setActive(idx);
                });

                dropdown.appendChild(item);
            });

            items = dropdown.querySelectorAll('.suggestion-item');
            dropdown.classList.add('open');
        }

        function highlightMatch(text, query) {
            const lower = text.toLowerCase();
            const qLower = query.toLowerCase();
            const start = lower.indexOf(qLower);
            if (start === -1) return escapeHtml(text);
            const end = start + qLower.length;
            return (
                escapeHtml(text.slice(0, start)) +
                '<mark>' + escapeHtml(text.slice(start, end)) + '</mark>' +
                escapeHtml(text.slice(end))
            );
        }

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        function hideDropdown() {
            dropdown.classList.remove('open');
            dropdown.innerHTML = '';
            activeIndex = -1;
            items = [];
        }

        function selectItem(word) {
            // Replace only the last word, keeping previous words
            input.value = replaceLastWord(input.value, word) + ' ';
            hideDropdown();
            if (onSelect) onSelect(word);
            // Trigger input event so other listeners (e.g. table search) react
            input.dispatchEvent(new Event('input', { bubbles: true }));
            // Keep focus and cursor at end
            input.focus();
        }

        /* ── Keyboard navigation ── */
        function setActive(idx) {
            items.forEach(el => el.classList.remove('active'));
            activeIndex = idx;
            if (idx >= 0 && idx < items.length) {
                items[idx].classList.add('active');
                items[idx].scrollIntoView({ block: 'nearest' });
            }
        }

        /* ── Event listeners ── */
        const debouncedFetch = debounce((query) => {
            fetchSuggestions(query);
        }, debounceMs);

        input.addEventListener('input', () => {
            const lastWord = getLastWord(input.value);
            if (lastWord.length >= minChars) {
                debouncedFetch(lastWord);
            } else {
                hideDropdown();
            }
        });

        input.addEventListener('keydown', (e) => {
            if (!dropdown.classList.contains('open')) return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    setActive(activeIndex < items.length - 1 ? activeIndex + 1 : 0);
                    break;

                case 'ArrowUp':
                    e.preventDefault();
                    setActive(activeIndex > 0 ? activeIndex - 1 : items.length - 1);
                    break;

                case 'Enter':
                    if (activeIndex >= 0 && activeIndex < items.length) {
                        e.preventDefault();
                        const word = items[activeIndex].textContent;
                        selectItem(word);
                    }
                    break;

                case 'Escape':
                    hideDropdown();
                    break;
            }
        });

        // Close on click outside
        document.addEventListener('click', (e) => {
            if (!wrap.contains(e.target)) {
                hideDropdown();
            }
        });

        // Close on blur (with small delay so mousedown on item fires first)
        input.addEventListener('blur', () => {
            setTimeout(hideDropdown, 150);
        });
    }

    /* ── Global expose ── */
    window.initSuggestion = initSuggestion;
})();
