"""Clichés, AI stock phrasing, stock body language and redundancy."""

from __future__ import annotations

import re

from ..text import Document
from .base import Pattern, PatternRule, Rule, RuleContext, register


@register
class AIStockPhrases(PatternRule):
    id = "ai_stock_phrases"
    name = "AI stock phrases"
    category = "cliche"
    description = "Phrases that turn up constantly in AI-generated fiction (“a testament to”, “something shifted”, “maybe, just maybe”)."
    message = "Stock phrasing that appears constantly in AI-generated fiction. It reads as generic rather than observed."
    suggestion = "Say the specific thing this phrase is standing in for, in words this narrator would use."
    patterns = (
        Pattern(r"\btestament\s+to\b"),
        Pattern(r"\bliving,?\s+breathing\b"),
        Pattern(r"\b(?:sunlight|light|moonlight|starlight)\s+filter(?:ed|ing|s)\s+(?:through|in)\b", severity="low"),
        Pattern(r"\bdappled\s+(?:sunlight|shadows?|light)\b", severity="low"),
        Pattern(r"\bshadows?\s+(?:that\s+)?(?:danced|dancing|danced)\b"),
        Pattern(r"\b(?:forest|trees|wind|walls|house|city|shadows)\s+whispered\s+(?:secrets|of)\b"),
        Pattern(r"\btapestry\s+of\b"),
        Pattern(r"\bsymphony\s+of\b"),
        Pattern(r"\bkaleidoscope\s+of\b"),
        Pattern(r"\b(?:let|letting|lets)\s+out\s+a\s+breath\s+(?:\w+\s+)?{SUBJ}\s+(?:didn{APOS}t|did\s+not|hadn{APOS}t)\s+(?:know|realized?|realised?)\b", severity="high"),
        Pattern(r"\bbreath\s+{SUBJ}\s+(?:didn{APOS}t|did\s+not|hadn{APOS}t)\s+(?:know|realized?|realised?)\s+{SUBJ}\s+(?:was|were|had\s+been|{APOS}d\s+been)\s+holding\b", severity="high"),
        Pattern(r"\bsomething\s+(?:shifted|changed|broke|cracked|loosened)\s+(?:between\s+them|in\s+{PRON}\s+chest|inside\s+{OBJ}|in\s+{OBJ})\b", severity="high"),
        Pattern(r"\bsomething\s+shifted\b"),
        Pattern(r"\bthe\s+(?:silence|quiet)\s+(?:stretched|settled|lingered|hung|thickened|pressed)\b"),
        Pattern(r"\b(?:hung|hanging|hangs)\s+(?:heavy\s+)?(?:in\s+the\s+air|between\s+them)\b"),
        Pattern(r"\b(?:voice|words?|whisper)\s+(?:was\s+)?(?:barely\s+)?above\s+a\s+whisper\b"),
        Pattern(r"\b(?:a|the)\s+ghost\s+of\s+a\s+(?:smile|grin|laugh)\b"),
        Pattern(r"\bcouldn{APOS}t\s+help\s+but\b"),
        Pattern(r"\bin\s+that\s+moment\b", severity="low"),
        Pattern(r"\bfor\s+the\s+first\s+time\s+in\s+(?:a\s+long\s+time|years|forever|what\s+felt\s+like)\b"),
        Pattern(r"\bmaybe,?\s+just\s+maybe\b", severity="high"),
        Pattern(r"\bevery\s+fib(?:er|re)\s+of\s+{PRON}\s+being\b"),
        Pattern(r"\b(?:the|a)\s+weight\s+of\s+(?:it\s+all|the\s+world|{PRON}\s+words|the\s+moment|the\s+silence|everything|what\s+(?:she|he|they|i)\s+had\s+(?:done|said))\b"),
        Pattern(r"\b{PRON}\s+(?:[\w'’-]+\s+)?(?:eyes|gaze)\s+(?:holding|held)\b(?=\s+(?:a|an)\b)"),
        Pattern(r"\b(?:eyes|gaze)\s+that\s+held\b"),
        Pattern(r"\ba\s+(?:mix|mixture|blend)\s+of\s+[\w'’-]+\s+and\s+[\w'’-]+\b"),
        Pattern(r"\bthe\s+(?:air|room)\s+(?:was\s+|grew\s+|felt\s+)?(?:thick|heavy|electric|charged)\s+with\b"),
        Pattern(r"\b(?:smell|scent|tang)\s+of\s+ozone\b"),
        Pattern(r"\bpetrichor\b", severity="low"),
        Pattern(r"\bunspoken\s+(?:words|understanding|question|tension|promise|things)\b"),
        Pattern(r"\bheavy\s+with\s+(?:everything\s+)?(?:unspoken|unsaid)\b"),
        Pattern(r"\b(?:tension|silence|grief|fear)\s+(?:was\s+)?palpable\b"),
        Pattern(r"\b{SUBJ}\s+(?:didn{APOS}t|did\s+not)\s+(?:need|have)\s+to\s*[.!]", title="“He didn't have to.”"),
        Pattern(r"\bif\s+only\s+for\s+a\s+moment\b"),
        Pattern(r"\bnestled\b", severity="low"),
        Pattern(r"\bdelv(?:e|es|ed|ing)\s+(?:into|deeper)\b"),
        Pattern(r"\b(?:a|the)\s+beacon\s+of\b"),
        Pattern(r"\b(?:a|in)\s+stark\s+contrast\s+to\b"),
        Pattern(r"\btime\s+(?:seemed\s+to\s+)?(?:slow(?:ed)?|stretch(?:ed)?)\s+(?:down|to\s+a\s+crawl)?\b"),
        Pattern(r"\bthe\s+world\s+(?:seemed\s+to\s+)?(?:fell|fall|faded|fade|narrowed|narrow)\s+away\b"),
        Pattern(r"\b(?:the\s+)?(?:almost\s+)?imperceptibl[ey]\b", severity="low"),
        Pattern(r"\b(?:liminal|ethereal|otherworldly)\b", severity="low"),
        Pattern(r"\b{SUBJ}\s+(?:found|finds)\s+{REFL}\s+\w+ing\b"),
        Pattern(r"\b(?:the|a)\s+(?:faintest|barest|smallest)\s+(?:hint|trace|ghost|flicker)\s+of\b"),
        Pattern(r"\ba\s+(?:hint|flicker|flash)\s+of\s+(?:something|amusement|sadness|recognition|emotion)\b"),
        Pattern(r"\bsomething\s+(?:she|he|they|i)\s+(?:couldn{APOS}t|could\s+not)\s+(?:quite\s+)?(?:name|place|identify|define)\b", severity="high"),
        Pattern(r"\band\s+something\s+(?:else|darker|deeper|older|more\s+\w+)\b"),
        Pattern(r"\bcarefully\s+(?:neutral|blank|controlled|even)\b"),
        Pattern(r"\bdespite\s+{REFL}\b"),
        Pattern(r"\b(?:a|the)\s+comfortable\s+silence\b"),
        Pattern(r"\bpadded\s+(?:across|into|over|down|through|to|toward|towards)\b", severity="low"),
        Pattern(r"\bsomewhere(?:\s+in\s+the\s+distance)?,?\s+an?\s+(?:dog|owl|bird|siren|car\s+alarm)\s+\w+\b", title="“Somewhere, a dog barked.”"),
        Pattern(r"\bthe\s+[\w'’-]+\s+of\s+it\s+all\b"),
        Pattern(r"\ba\s+(?:stark|sharp|painful|grim|cruel|bitter|harsh)\s+reminder\b"),
        Pattern(r"\b(?:steel(?:ed|ing)|brac(?:ed|ing))\s+{REFL}\b", severity="low"),
        Pattern(r"\ba\s+quiet\s+(?:strength|resolve|determination|understanding|intensity|defiance)\b"),
    )


@register
class Cliches(PatternRule):
    id = "cliches"
    name = "Clichés"
    category = "cliche"
    description = "Worn-out expressions (“blood ran cold”, “time stood still”, “a chill ran down her spine”)."
    message = "A cliché: the reader has seen it so often it no longer produces a picture or a feeling."
    suggestion = "Replace it with a fresh, specific observation, or cut it and see if the sentence still works."
    patterns = (
        Pattern(r"\bheart\s+(?:pounded|pounding|hammered|hammering|raced|racing|thundered|thundering|thudded)\b", severity="low"),
        Pattern(r"\b(?:blood|veins)\s+(?:ran|run|runs|turned|turn)\s+(?:cold|to\s+ice)\b"),
        Pattern(r"\bdead\s+of\s+(?:night|winter)\b"),
        Pattern(r"\b(?:a\s+)?(?:chill|shiver)s?\s+(?:ran|run|running|went|crept|raced|snaked|shot)\s+(?:up|down)\s+{PRON}\s+spine\b"),
        Pattern(r"\bsen(?:t|ding|ds)\s+(?:a\s+)?(?:chill|shiver)s?\s+(?:down|up|through)\b"),
        Pattern(r"\bbutterflies\s+in\s+{PRON}\s+stomach\b"),
        Pattern(r"\btime\s+stood\s+still\b"),
        Pattern(r"\b(?:frozen|rooted)\s+(?:in\s+place|to\s+the\s+spot)\b"),
        Pattern(r"\b(?:deafening|thunderous)\s+silence\b|\bsilence\s+was\s+deafening\b"),
        Pattern(r"\bpregnant\s+pause\b"),
        Pattern(r"\b(?:piercing|steely|icy)\s+(?:blue|grey|gray|green)\s+eyes\b"),
        Pattern(r"\braven(?:-black)?\s+(?:hair|locks|tresses)\b"),
        Pattern(r"\bporcelain\s+skin\b"),
        Pattern(r"\b{PRON}\s+(?:\w+\s+)?orbs\b"),
        Pattern(r"\bchiseled\s+(?:jaw|features|abs|chest)\b"),
        Pattern(r"\b(?:breath|heart)\s+caught\s+in\s+{PRON}\s+throat\b"),
        Pattern(r"\bheart\s+skipped\s+a\s+beat\b"),
        Pattern(r"\blump\s+(?:\w+\s+)?in\s+{PRON}\s+throat\b"),
        Pattern(r"\b(?:knot|pit)\s+(?:in|of)\s+{PRON}\s+stomach\b"),
        Pattern(r"\bwith\s+bated\s+breath\b"),
        Pattern(r"\bin\s+the\s+nick\s+of\s+time\b"),
        Pattern(r"\ball\s+hell\s+broke\s+loose\b"),
        Pattern(r"\b(?:white|pale)\s+as\s+(?:a\s+)?(?:sheet|ghost)\b"),
        Pattern(r"\b(?:cold\s+as\s+ice|light\s+as\s+a\s+feather|quiet\s+as\s+a\s+mouse|still\s+as\s+(?:a\s+)?(?:stone|statue|death))\b"),
        Pattern(r"\b(?:seething|boiling)\s+with\s+(?:rage|anger)\b|\bblood\s+boil(?:ed|ing)\b"),
        Pattern(r"\b{PRON}\s+mind\s+(?:raced|racing|was\s+racing)\b|\bthoughts\s+(?:raced|racing)\b"),
        Pattern(r"\btears\s+(?:welled|welling)\s+(?:up\s+)?in\s+{PRON}\s+eyes\b"),
        Pattern(r"\ba\s+single\s+tear\b"),
        Pattern(r"\bat\s+the\s+end\s+of\s+the\s+day\b"),
        Pattern(r"\bonly\s+time\s+will\s+tell\b"),
        Pattern(r"\bcalm\s+before\s+the\s+storm\b"),
        Pattern(r"\bagainst\s+all\s+odds\b"),
        Pattern(r"\bthe\s+last\s+straw\b"),
        Pattern(r"\bspoke\s+volumes\b"),
        Pattern(r"\ba\s+sight\s+for\s+sore\s+eyes\b"),
        Pattern(r"\bnerves\s+of\s+steel\b"),
        Pattern(r"\bheart\s+of\s+gold\b"),
        Pattern(r"\blike\s+a\s+deer\s+(?:caught\s+)?in\s+(?:the\s+)?headlights\b"),
        Pattern(r"\bhead\s+over\s+heels\b"),
        Pattern(r"\bmoment\s+of\s+truth\b"),
        Pattern(r"\bfell\s+on\s+deaf\s+ears\b"),
        Pattern(r"\bwithout\s+a\s+(?:second\s+thought|moment{APOS}s\s+hesitation)\b"),
        Pattern(r"\bhit\s+(?:her|him|them|me)\s+like\s+a\s+(?:ton\s+of\s+bricks|freight\s+train|truck)\b"),
        Pattern(r"\beyes\s+(?:like|as\s+wide\s+as)\s+saucers\b"),
        Pattern(r"\bfrom\s+ear\s+to\s+ear\b"),
        Pattern(r"\b(?:their|our)\s+eyes\s+met\b", severity="low"),
        Pattern(r"\bdarkness\s+(?:consumed|engulfed|swallowed)\b"),
        Pattern(r"\bit\s+was\s+a\s+dark\s+and\s+stormy\s+night\b"),
        Pattern(r"\bout\s+of\s+nowhere\b", severity="low"),
        Pattern(r"\bthe\s+sound\s+of\s+silence\b"),
    )


@register
class StockBodyLanguage(PatternRule):
    id = "stock_body_language"
    name = "Stock body language"
    category = "cliche"
    description = "Go-to physical reactions (jaw tightening, breath hitching, eyes widening). Flagged only when they pile up."
    has_sensitivity = True
    sensitivity_help = "How many stock beats before any are flagged (low: 6, medium: 4, high: 2)."
    min_matches = (6, 4, 2)
    severity = "low"
    message = (
        "A stock body-language beat. One or two are invisible; AI prose cycles through the same small set "
        "(jaws, breaths, eyes, stomachs) instead of finding gestures specific to this character."
    )
    suggestion = "Find a gesture only this character would make, or cut the beat and let the dialogue carry it."
    patterns = (
        Pattern(r"\bjaw\s+(?:clenched|tightened|tight|set|working|ticked)\b|\bclenched\s+{PRON}\s+jaw\b"),
        Pattern(r"\b(?:clenched|balled)\s+{PRON}\s+(?:fists|hands)\b|\bfists\s+clenched\b|\bhands\s+(?:balled|curled)\s+into\s+fists\b"),
        Pattern(r"\bbreath\s+(?:hitched|caught|stuttered)\b"),
        Pattern(r"\blet\s+out\s+a\s+(?:shaky|slow|long|ragged|shuddering|trembling)\s+breath\b"),
        Pattern(r"\b(?:took|drew)\s+a\s+(?:deep|steadying|shaky|long|slow)\s+breath\b"),
        Pattern(r"\bexhaled\s+(?:slowly|sharply)\b"),
        Pattern(r"\bswallowed\s+hard\b"),
        Pattern(r"\bthroat\s+(?:tightened|constricted|closed|thickened|worked)\b"),
        Pattern(r"\beyes\s+(?:widened|narrowed|softened|darkened|flashed|glistened)\b"),
        Pattern(r"\bheart\s+(?:sank|clenched|twisted|ached|stuttered|lurched)\b"),
        Pattern(r"\bstomach\s+(?:dropped|lurched|churned|flipped|twisted|knotted)\b"),
        Pattern(r"\blips\s+(?:pressed|thinned)\s+(?:into\s+a\s+(?:thin|hard|tight)\s+line|together)\b|\bpressed\s+{PRON}\s+lips\s+together\b"),
        Pattern(r"\b(?:brow|brows|forehead)\s+(?:furrowed|creased|knitted|knit)\b|\bfurrowed\s+{PRON}\s+brow\b"),
        Pattern(r"\bmuscle\s+(?:ticked|twitched|jumped|feathered)\s+in\s+{PRON}\s+jaw\b"),
        Pattern(r"\bran\s+a\s+hand\s+(?:through|over)\s+{PRON}\s+(?:hair|face)\b"),
        Pattern(r"\bnodded\s+slowly\b|\bshook\s+{PRON}\s+head\s+slowly\b"),
        Pattern(r"\bshoulders\s+(?:slumped|sagged|tensed|stiffened)\b"),
        Pattern(r"\bknuckles\s+(?:went\s+|turning\s+|turned\s+)?white\b|\bwhite-knuckled\b"),
        Pattern(r"\b(?:smile|grin)\s+(?:tugged|played|pulled|crept)\s+(?:at|across|onto)\b"),
        Pattern(r"\bcorners?\s+of\s+{PRON}\s+(?:mouth|lips)\s+(?:twitched|quirked|lifted|curved|tugged|turned\s+up)\b"),
        Pattern(r"\b{PRON}\s+(?:mouth|lips)\s+quirked\b"),
        Pattern(r"\b{PRON}\s+gaze\s+(?:softened|hardened|lingered|flicked|dropped)\b"),
        Pattern(r"\b{PRON}\s+chest\s+(?:tightened|tighten|tightening|constricted|ached)\b|\bmade\s+{PRON}\s+chest\s+tighten\b"),
    )


@register
class Redundancy(PatternRule):
    id = "redundancy"
    name = "Redundant wording"
    category = "cliche"
    description = "Words that repeat what's already said (“nodded her head”, “whispered quietly”). Most have a one-click fix."
    severity = "low"
    message = "Redundant wording: part of the phrase repeats what the rest already says."
    suggestion = "Use the shorter form."
    patterns = (
        Pattern(r"\b(?P<v>nod(?:ded|s|ding)?)\s+{PRON}\s+head\b", replacement=r"\g<v>", message="“Nodded her head”: you can only nod your head."),
        Pattern(r"\b(?P<v>shrug(?:ged|s|ging)?)\s+{PRON}\s+shoulders\b", replacement=r"\g<v>", message="“Shrugged his shoulders”: you can only shrug your shoulders."),
        Pattern(r"\b(?P<v>blink(?:ed|s|ing)?)\s+{PRON}\s+eyes\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>whisper(?:ed|s|ing)?)\s+(?:softly|quietly)\b", replacement=r"\g<v>", message="A whisper is already quiet."),
        Pattern(r"\b(?P<v>murmur(?:ed|s|ing)?)\s+(?:softly|quietly)\b", replacement=r"\g<v>", message="A murmur is already quiet."),
        Pattern(r"\b(?P<v>shout(?:ed|s|ing)?|yell(?:ed|s|ing)?|scream(?:ed|s|ing)?)\s+loudly\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>thought|thinks|thinking)\s+to\s+{REFL}\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>stood|stands|standing)\s+up\s+(?:to|on)\s+{PRON}\s+feet\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>saw|seen|see)\s+with\s+{PRON}\s+own\s+eyes\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>heard|hear)\s+with\s+{PRON}\s+own\s+ears\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>smil(?:ed|es|ing))\s+(?:happily|cheerfully)\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>frown(?:ed|s|ing)?)\s+(?:unhappily|sadly)\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>sob(?:bed|s|bing)?)\s+(?:tearfully|sadly)\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<a>a\s+)?brief\s+moment\b", replacement=r"\g<a>moment"),
        Pattern(r"\bunexpected\s+surprise\b", replacement="surprise"),
        Pattern(r"\bend\s+result\b", replacement="result"),
        Pattern(r"\bfinal\s+outcome\b", replacement="outcome"),
        Pattern(r"\bpast\s+history\b", replacement="history"),
        Pattern(r"\bfree\s+gift\b", replacement="gift"),
        Pattern(r"\beach\s+and\s+every\b", replacement="every"),
        Pattern(r"\bfirst\s+began\b", replacement="began"),
        Pattern(r"\b(?P<v>return(?:ed|s|ing)?)\s+back\b", replacement=r"\g<v>"),
        Pattern(r"\b(?P<v>join(?:ed|s|ing)?)\s+together\b", replacement=r"\g<v>"),
        Pattern(r"\bclose\s+proximity\b", replacement="proximity"),
        Pattern(r"\b(?:completely|totally|utterly)\s+(?P<v>destroyed|annihilated|demolished|obliterated)\b", replacement=r"\g<v>"),
        Pattern(r"\babsolutely\s+(?P<v>essential|certain|necessary)\b", replacement=r"\g<v>"),
        Pattern(r"\bpitch[\s-]black\s+darkness\b", replacement="darkness"),
        Pattern(r"\bin\s+order\s+to\b", replacement="to", message="“In order to” is usually just “to”."),
        Pattern(
            r"\b(?:began|begins|started|starts)\s+to\b(?=\s+[a-z])",
            title="“Began to…”",
            message="“Began to / started to” often delays the action.",
            suggestion="Use the plain verb (“she walked”, not “she began to walk”) unless the start of the action matters.",
        ),
    )


AI_FAVOURED_NAMES = {
    "Elara", "Kael", "Kaelen", "Lyra", "Seraphina", "Thorne", "Voss", "Zephyr", "Nyx", "Aurelia",
    "Cassius", "Lysander", "Isolde", "Evander", "Liora", "Aldric", "Corvin", "Vesper", "Caelum",
    "Solenne", "Mirelle", "Theron", "Riven", "Elowen", "Kaelith", "Sylas", "Aric", "Eryndor",
    "Kestrel", "Seraphine", "Valerius", "Aelira",
}


@register
class AIFavouredNames(Rule):
    id = "ai_names"
    name = "AI-favoured names"
    category = "cliche"
    description = "Character names that appear unusually often in AI-generated fiction (Elara, Kael, Lyra, Seraphina…)."

    def check(self, doc: Document, ctx: RuleContext):
        results = []
        seen = set()
        for start, end, word in doc.words:
            base = re.sub(r"['’]s$", "", word)
            if base in AI_FAVOURED_NAMES and base not in seen:
                seen.add(base)
                results.append(
                    self.finding(
                        doc,
                        start,
                        start + len(base),
                        f"“{base}” turns up unusually often in AI-generated fiction, so readers may notice it.",
                        "If you chose it deliberately, ignore this. Otherwise pick a name rooted in the "
                        "character's background, era and setting.",
                        severity="low",
                    )
                )
        return results
