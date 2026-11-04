"""Generate BOM.md from the parts list below, so every total is computed, not typed.

Price status:  L = seen on a live listing / search result on DATE (verify before ordering)
               E = estimate, no live price found (typical online / hardware-store price)
"""
import os

DATE = "2026-10-22"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMZ = "https://www.amazon.com/s?k="


def amz(q):
    return AMZ + q.replace(" ", "+")


# (group, item, spec, qty, price for the line, status, url, note)
BUY = [
    ("Drive", "Motor", "775 DC motor, 12 V ~4,000 RPM (sold as \"12 V 4000 / 24 V 8000 RPM\"), 5 mm shaft", 1, 12.99, "L",
     "https://www.walmart.com/c/kp/volt-dc-motor", "Run it on 12 V. The model is checked for this 4,000 RPM speed only; the clash check fails at 6,000 and 8,000 RPM"),
    ("Drive", "Speed control", "PWM DC motor speed controller, 12–24 V, 10 A, knob with on/off", 1, 7.70, "L",
     "https://www.walmart.com/ip/13872166347", ""),
    ("Drive", "Power supply", "12 V 10 A (120 W) power brick + 5.5 mm barrel-jack pigtail", 1, 11.00, "L",
     "https://www.ebay.com/itm/396982511231", "$9.17 listing + ~$1 pigtail. Any 12 V supply that gives 8 A or more works."),
    ("Drive", "Motor pulley", "GT2 20-tooth aluminum pulley, 5 mm bore (3D-printer part)", 1, 1.50, "E", amz("GT2 20 tooth pulley 5mm bore"), "Usually sold in 5-packs"),
    ("Drive", "Belt", "GT2 6 mm closed-loop belt, 500 mm", 1, 5.73, "L", "https://www.ebay.com/itm/283194907394", ""),
    ("Arbor", "Bolt", "1/2-13 × 14 in hex bolt, ≥ 1¼ in of thread; pick one that rolls straight", 1, 4.00, "E", amz("1/2-13 x 14 hex bolt"),
     "The model is checked for a 14 in bolt only"),
    ("Arbor", "Nut and washers", "1/2-13 nut + one 1/2 × 1½ in fender washer", 1, 1.50, "E", amz("1/2 fender washer 1-1/2"), ""),
    ("Arbor", "Bearings", "R8-2RS, 1/2 × 1⅛ × 5/16 in (10-pack; 2 used)", 1, 7.75, "L",
     "https://www.shopabunda.com/products/pgn-10-pack-r8-2rs-bearing-lubricated-chrome-steel-sealed-ball-bearing-1-2-x1-1-8-x5-16-bearings-with-rubber-seal-high-rpm-support", ""),
    ("Water", "Pump", "12 V mini submersible pump, 240 L/h", 1, 10.15, "L", "https://www.walmart.com/ip/17108059565", "$7.16 + $2.99 shipping; runs off the same 12 V supply"),
    ("Water", "Drip lines", "Aquarium airline tube 6 mm OD, 4 m + 5 airline control valves", 1, 6.00, "E", amz("aquarium airline tubing with control valves"), ""),
    ("Base", "Board", "1×12 pine, 24 in (or any ¾ in plywood scrap ≥ 610 × 286 mm)", 1, 6.00, "E", amz("1x12 pine board 2 ft"), ""),
    ("Base", "Screws and wire", "~20 #8 × 1¼ in wood screws; 8 × M4 × 30 + nuts; 2 m of 18 AWG wire", 1, 6.00, "E", amz("M4 x 30 screws nuts assortment"), ""),
]

WHEELS = [
    ("Wheels", "4 × 6 × 1½ in diamond wheels, 1 in arbor: 80 + 220 hard, 280 + 600 resin (~$24–36 each)", 4, 30.00, "L", "https://www.walmart.com/c/kp/lapidary-wheels"),
    ("End-disk pads", "6 in hook-and-loop diamond pads (1,200 → 8,000 range) + a 6 in PSA hook-and-loop sheet", 1, 25.00, "E", amz("6 inch diamond polishing pads hook and loop")),
    ("Dressing stick", "Silicon carbide dressing stick", 1, 8.00, "E", amz("silicon carbide dressing stick")),
]


def money(v):
    return f"${v:,.2f}"


def link(url):
    return f"[{'search' if url.startswith(AMZ) else 'link'}]({url})"


def main():
    out = []
    w = out.append
    w("# Bill of materials")
    w("")
    w(f"Everything is bought new. Prices checked **{DATE}**: **L** = seen on a listing that day, **E** = typical price. Check before buying.")
    w("")
    w("| # | Group | Item | Spec | Qty | Price | Status | Source | Note |")
    w("|---|---|---|---|---|---|---|---|---|")
    tot = 0.0
    for i, (g, item, spec, qty, price, st, url, note) in enumerate(BUY, 1):
        tot += price
        w(f"| {i} | {g} | {item} | {spec} | {qty} | {money(price)} | {st} | {link(url)} | {note} |")
    w(f"| | | **Total** | | | **{money(tot)}** | | | |")
    w("")
    w("Plus about 2.5 kg of PETG for the prints (~$35–40 if you don't have it).")
    w("")
    w("## Wheels and pads (consumables)")
    w("")
    w("| Item | Spec | Qty | Price | Status | Source |")
    w("|---|---|---|---|---|---|")
    wheels = 0.0
    for item, spec, qty, unit, st, url in WHEELS:
        wheels += unit * qty
        w(f"| {item} | {spec} | {qty} | {money(unit * qty)} | {st} | {link(url)} |")
    w("")
    w(f"**Machine {money(tot)} + wheels and pads {money(wheels)} = {money(tot + wheels)}.**")
    w("")
    w("Ways to spend less: use scrap wood, buy 2 bearings instead of a 10-pack, and use any 12 V supply you already have (an old PC power supply or LED-strip brick). That brings the machine to roughly $60.")
    open(os.path.join(ROOT, "BOM.md"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print(f"buy {tot:.2f}  wheels {wheels:.2f}  total {tot + wheels:.2f}")


if __name__ == "__main__":
    main()
