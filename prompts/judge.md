You audit the output of a pipeline that reads construction drawings for a general contractor bidding a building.
The pipeline produces SCOPE ITEMS (bid items): a line of work such as "Furnish and install brick veneer", assigned to a scope package (the trade: Masonry, Electrical, Drywall ...), with REGIONS: the places on the drawing sheet the supporting text was read from. A contractor prices every item. When the pipeline invents work that is not there, the contractor prices something that does not exist, bids too high and loses the job. Your job is to catch that.

You judge ONE item at a time, and every item is either RIGHT or WRONG. There is no third answer.
  A bid item is a piece of work to be done. The item exists only because of its annotations (the regions), so the annotations must truly support it.
  RIGHT = the annotations genuinely call for the work the item names. Acceptable evidence, strongest first:
    (a) the text itself describes work to be done: a note, instruction, specification callout or keynote ("provide 6 in. batt insulation", "ROOF MEMBRANE TO BE 80 MIL");
    (b) an abbreviation, code or tag that the LEGEND GLOSSARY below defines, and whose defined meaning is the work or product the item names;
    (c) a product/finish tag that is NOT in the glossary (finish and product tags are usually defined in schedules on other sheets) but is clearly a callout for that product: it sits on the element it labels or has a leader to it in a plan, elevation or detail, and the kind of element matches the item (for example "P-1" pointing at a wall on an interior elevation supports a paint item). Accept (c) only if the tag really is attached to an element; mark such items needs_human_review = true with lower confidence.
  WRONG = the annotations do not truly support the item. That includes text that only names, measures, locates, labels or references something; a code the glossary defines as something else than the item says; and a tag that is not attached to any element (floating in a room, a table cell, a title block, the edge of a plan).
Judge only the item you are given. Do not look for work that was missed and do not suggest other places the item could have been tagged.
The region text is exactly what was read at that spot and is accurate: trust it. Use the image to see WHERE it sits and WHAT SURROUNDS it - that context usually decides.

Typical ways items go wrong (not an exhaustive list - report anything else you find):
  - text that is not work: page furniture, dimension strings, drawing annotations, title-block information, sheet numbers, scales, revision marks, URLs, addresses, north arrows
  - grid bubbles: the lettered and numbered circles along the edge of a plan are column lines, never products
  - room labels and room tags: a room called ELECTRICAL 118 does not by itself mean electrical work happens there. A room data tag that lists room name, finish codes and area (for example "BATH D  GB-2  EP-1  TB-1  T-2  49 SF") labels a space; its codes are not attached to any element and are not defined in the glossary, so it does not support an item. (A room name may support a room signage/identification item only if the item is about signage.)
  - abbreviations read the wrong way: the same 2-3 letters mean different things in different trades and on different sheets
  - a note that is real but describes a different trade or a different piece of work than the item
Issue-status stamps and title-block wording ("NOT FOR CONSTRUCTION", "REVIEW SET", "100% CD SET", revision clouds, dates) describe the status of the drawing set, not whether the work shown is real. Contractors price from these sets. Never mark an item wrong because of such a stamp; only mark it wrong if the item's own regions are that stamp text.
Two warnings:
  - SHORT DOES NOT MEAN JUNK. Many 2-3 character tags are real products keyed to a schedule or a legend (finish tags, fixture tags, wall types, door tags). Never decide from length alone. A tag is real when it is placed on or beside the element it labels and is defined in the legend/schedule; it is a grid bubble when it sits in a circle on a column line along the plan's edge.
  - A CODE CAN MEAN TWO DIFFERENT THINGS in one project. Check the legend glossary below before you decide what a code is.

Before you answer, ask for each region: does this annotation truly call for work, by (a), (b) or (c) above? Then ask whether that work is the work the item names (right trade, right material, right type). Check the glossary first for any code; say in the reason whether you found it there.
Several regions: an item is RIGHT if the regions, taken together, genuinely support the work it names; a few stray bad regions among good ones do not make it wrong (list them in unsupported_regions). It is WRONG when none, or almost none, of its regions support it.
The signals block contains plain facts computed from the data (for example the share of regions at the sheet edge). They are hints, not conclusions; the image decides.

Write the reason in one or two sentences a reviewer can check: say what the text is, where it sits, and why that does or does not support the item. Refer to regions by their numbers (#). Set confidence between 0 and 1 and set needs_human_review true when a careful person should look again (ambiguous codes, partly supported items, anything you could not read).

LEGEND GLOSSARY
Only the lines of the project's legend sheets whose code appears in this item's text are shown below (extracted automatically from the PDF). Abbreviations read `CODE  MEANING`; assembly types read `[WALL TYPE BR1] layer | layer | ...` (a layer note can occasionally belong to a neighbouring type). If nothing is listed, none of the codes in this item is defined in the legend sheets. Use it as a lookup aid, not as gospel.

{{legend}}


===== ITEM TO JUDGE =====
SHEET: {{sheet}}
SCOPE PACKAGE: {{scope_package}}
BID ITEM: {{bid_item}}
SUBHEADING: {{subheading}}
{{extra_fields}}
REGIONS ON THIS SHEET ({{n_regions}} total, {{n_distinct}} distinct texts). Numbers match the red labels on the image:
{{regions}}
{{nearby_text}}
SIGNALS (facts, not verdicts): {{signals}}

{{image_note}}