"""
USB raw thermal printer service for RETSOL RTP-81 and 55mm/58mm ESC/POS printers via CUPS & direct USB.
"""

import glob
import logging
import os
import subprocess
from django.conf import settings

logger = logging.getLogger(__name__)

# ESC/POS Command Constants
ESC = b"\x1b"
GS = b"\x1d"

CMD_INIT = ESC + b"@"
CMD_ALIGN_LEFT = ESC + b"a\x00"
CMD_ALIGN_CENTER = ESC + b"a\x01"
CMD_BOLD_ON = ESC + b"E\x01"
CMD_BOLD_OFF = ESC + b"E\x00"
CMD_CUT = GS + b"V\x00"  # GS V \x00 cut command


def send_to_cups_printer(data_bytes, printer_name=None):
    """Send raw data to CUPS printer queue with -o raw."""
    printer = printer_name or getattr(settings, "CUPS_PRINTER_NAME", "RTP81")
    try:
        subprocess.run(
            ["lp", "-d", printer, "-o", "raw"],
            input=data_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        return True, f"Sent to printer '{printer}' successfully."
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode("utf-8", "ignore").strip() or str(e)
        logger.warning("CUPS raw print error: %s", err)
        return False, err
    except FileNotFoundError:
        return False, "lp command not found on system."
    except Exception as e:
        logger.error("CUPS error: %s", e)
        return False, str(e)


def get_usb_printer_device():
    """Find fallback USB character device."""
    configured_port = getattr(settings, "USB_PRINTER_PORT", "/dev/usb/lp0")
    if configured_port and os.path.exists(configured_port):
        return configured_port

    for dev in glob.glob("/dev/usb/lp*") + glob.glob("/dev/lp*"):
        if os.path.exists(dev):
            return dev

    return configured_port


def send_to_usb_printer(data_bytes, printer_name=None, port=None):
    """
    Send raw bytes to printer.
    Primary: CUPS raw queue ('lp -d RTP81 -o raw').
    Fallback: Direct character device ('/dev/usb/lp0').
    """
    # 1. Primary: CUPS raw print
    cups_success, cups_msg = send_to_cups_printer(data_bytes, printer_name=printer_name)
    if cups_success:
        return True, cups_msg

    # 2. Fallback: Direct character device
    device_path = port or get_usb_printer_device()
    if os.path.exists(device_path):
        try:
            with open(device_path, "wb") as printer:
                printer.write(data_bytes)
                printer.flush()
            return True, f"Printed directly via {device_path}."
        except Exception as e:
            return False, f"CUPS failed ({cups_msg}); Direct write to {device_path} failed: {e}"

    return False, f"CUPS print failed ({cups_msg}); Device not found at '{device_path}'."


def format_invoice_for_usb_print(invoice, width=32):
    """
    Format invoice into raw ESC/POS bytes matching 55mm format:
    echo -e "\\x1B\\x40\\x1B\\x61\\x01\\x1B\\x45\\x01GarageFlow\\x1B\\x45\\x00..." | lp -d RTP81 -o raw
    """
    buf = bytearray()
    div_double = (b"=" * width) + b"\n"
    div_single = (b"-" * width) + b"\n"

    # 1. Header (Centered, bold title)
    buf.extend(CMD_INIT + CMD_ALIGN_CENTER + CMD_BOLD_ON + b"GarageFlow" + CMD_BOLD_OFF + b"\n")
    buf.extend(b"Automotive Workshop & Services\n")
    buf.extend(b"TAX INVOICE / RECEIPT\n")
    buf.extend(div_double)

    # 2. Meta (Left aligned)
    buf.extend(CMD_ALIGN_LEFT)
    buf.extend(f"Invoice No: {invoice.invoice_number}\n".encode("ascii", "ignore"))
    date_str = invoice.created_at.strftime("%d/%m/%Y %I:%M %p")
    buf.extend(f"Date      : {date_str}\n".encode("ascii", "ignore"))

    cashier = "Admin"
    if invoice.created_by:
        cashier = (
            getattr(invoice.created_by, "first_name", "")
            or getattr(invoice.created_by, "username", "")
            or getattr(invoice.created_by, "phone", "")
            or str(invoice.created_by)
        )
    buf.extend(f"Cashier   : {cashier}\n".encode("ascii", "ignore"))
    buf.extend(div_single)

    # 3. Customer & Vehicle
    buf.extend(f"Customer  : {invoice.customer.name}\n".encode("ascii", "ignore"))
    if getattr(invoice.customer, "phone", None):
        buf.extend(f"Phone     : {invoice.customer.phone}\n".encode("ascii", "ignore"))

    if invoice.job_card:
        buf.extend(f"Job Card  : {invoice.job_card.job_card_number}\n".encode("ascii", "ignore"))
        buf.extend(f"Vehicle No: {invoice.job_card.vehicle_number}\n".encode("ascii", "ignore"))
        if invoice.job_card.vehicle_model:
            model_name = f"{invoice.job_card.vehicle_model.make.name} {invoice.job_card.vehicle_model.model_name}"
            buf.extend(f"Model     : {model_name}\n".encode("ascii", "ignore"))
    else:
        buf.extend(b"Sale Type : Counter Sale\n")
    buf.extend(div_single)

    # 4. Items Table
    buf.extend(b"Item         Qty   Rate   Amount\n")
    buf.extend(div_single)

    items = list(invoice.invoice_items.all())
    total_qty = 0.0

    for item in items:
        total_qty += float(item.quantity)
        desc = (item.description or "").upper()
        buf.extend((desc[:width] + "\n").encode("ascii", "ignore"))

        if item.inventory and item.inventory.part_number:
            buf.extend(f"PN: {item.inventory.part_number}\n".encode("ascii", "ignore"))

        # Format line: 12 spaces, Qty, Rate, Amount -> total 32 chars
        prefix = " " * 12
        qty_val = float(item.quantity)
        rate_val = float(item.unit_price)
        amt_val = float(item.total_price)

        q = f"{qty_val:>4.2f} "
        r_str = f"{rate_val:.1f}" if rate_val >= 1000 and rate_val == int(rate_val) else f"{rate_val:.2f}"
        r = f"{r_str:>6} "
        a = f"{amt_val:>8.2f}"
        row = prefix + q + r + a
        buf.extend((row[:width] + "\n").encode("ascii", "ignore"))

    buf.extend(div_single)

    # 5. Totals
    buf.extend(f"Total Items: {len(items)} ({total_qty:.2f} qty)\n".encode("ascii", "ignore"))
    total_formatted = f"Rs. {float(invoice.total_amount):,.2f}"
    label = "TOTAL DUE:"
    spaces = max(1, width - len(label) - len(total_formatted))
    due_line = label + (" " * spaces) + total_formatted
    buf.extend(CMD_BOLD_ON + (due_line[:width] + "\n").encode("ascii", "ignore") + CMD_BOLD_OFF)
    buf.extend(div_single)

    # 6. Notes
    if invoice.notes:
        buf.extend(f"Notes: {invoice.notes}\n".encode("ascii", "ignore"))
        buf.extend(b"\n")

    # 7. Footer
    buf.extend(CMD_ALIGN_CENTER)
    buf.extend(b"Thank You! Drive Safe.\n")
    buf.extend(b"Computer Generated Invoice\n")
    buf.extend(b"Signature Not Required\n")
    buf.extend(CMD_ALIGN_LEFT)
    buf.extend(b"* Goods sold are not returnable\n")
    buf.extend(b"* Vehicle driven at owner's risk\n")
    buf.extend(b"* E. & O.E.\n\n\n\n\n")
    buf.extend(CMD_CUT)

    return bytes(buf)
