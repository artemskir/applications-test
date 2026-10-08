"""Detailed investigation of specific phone edge cases."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from normalizer import phone
from normalizer.models import RawCell

OUTPUT_FILE = Path(__file__).parent / 'bidi_detail_results.txt'


def log(message):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(message + '\n')


def test_devanagari_correct_digits():
    """Devanagari digits 89174005219 - correct values."""
    # Devanagari: ८=8, ९=9, १=1, ७=7, ४=4, ०=0, ०=0, ५=5, २=2, १=1, ९=9
    value = '\u0968\u0969\u0967\u0966\u096a\u0966\u0966\u0966\u0968\u0967\u0969'
    # Wait, let me recalculate: 8=0968, 9=0969, 1=0967, 7=096D, 4=096A, 0=0966, 0=0966, 5=096B, 2=0968, 1=0967, 9=0969
    # Actually: 0966=0, 0967=1, 0968=2, 0969=3, 096A=4, 096B=5, 096C=6, 096D=7, 096E=8, 096F=9
    # So 89174005219 = 096E 096F 0967 096D 096A 0966 0966 096B 0968 0967 096F
    value = '\u096e\u096f\u0967\u096d\u096a\u0966\u0966\u096b\u0968\u0967\u096f'
    result = phone.analyze(RawCell(value))
    log(f'Devanagari correct: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')
    # Should be +79174005219 if Nd conversion works


def test_fullwidth_semicolon_vs_plus():
    """Fullwidth semicolon (U+FF1B) vs fullwidth plus (U+FF0B)."""
    # Fullwidth semicolon - should NOT be treated as +
    value_semicolon = '\uff1b\uff17\uff19\uff11\uff17\uff14\uff10\uff10\uff15\uff12\uff11\uff19'
    result = phone.analyze(RawCell(value_semicolon))
    log(f'Fullwidth semicolon: input={repr(value_semicolon)}, canonical={result.canonical}, codes={result.codes}')

    # Fullwidth plus - SHOULD be treated as +
    value_plus = '\uff0b\uff17\uff19\uff11\uff17\uff14\uff10\uff10\uff15\uff12\uff11\uff19'
    result2 = phone.analyze(RawCell(value_plus))
    log(f'Fullwidth plus: input={repr(value_plus)}, canonical={result2.canonical}, codes={result2.codes}')


def test_emoji_after_phone():
    """Emoji after phone number."""
    value = '89174005219\U0001f4de'
    result = phone.analyze(RawCell(value))
    log(f'Emoji: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_combining_mark_after_phone():
    """Combining acute accent after phone."""
    value = '89174005219\u0301'
    result = phone.analyze(RawCell(value))
    log(f'Combining: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_variation_selector_after_phone():
    """Variation selector U+FE0F after phone."""
    value = '89174005219\ufe0f'
    result = phone.analyze(RawCell(value))
    log(f'VS16: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_keycap_after_phone():
    """Enclosing keycap U+20E3 after phone."""
    value = '89174005219\u20e3'
    result = phone.analyze(RawCell(value))
    log(f'Keycap: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_emoji_before_phone():
    """Emoji before phone number."""
    value = '\U0001f4de89174005219'
    result = phone.analyze(RawCell(value))
    log(f'Emoji before: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_combining_mark_before_phone():
    """Combining mark before phone."""
    value = '\u030189174005219'
    result = phone.analyze(RawCell(value))
    log(f'Combining before: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_variation_selector_before_phone():
    """Variation selector before phone."""
    value = '\ufe0f89174005219'
    result = phone.analyze(RawCell(value))
    log(f'VS16 before: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_keycap_before_phone():
    """Keycap before phone."""
    value = '\u20e389174005219'
    result = phone.analyze(RawCell(value))
    log(f'Keycap before: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_emoji_in_middle_of_phone():
    """Emoji in middle of phone digits."""
    value = '89174\U0001f4de005219'
    result = phone.analyze(RawCell(value))
    log(f'Emoji middle: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_combining_mark_in_middle():
    """Combining mark in middle of phone."""
    value = '89174\u0301005219'
    result = phone.analyze(RawCell(value))
    log(f'Combining middle: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_variation_selector_in_middle():
    """Variation selector in middle of phone."""
    value = '89174\ufe0f005219'
    result = phone.analyze(RawCell(value))
    log(f'VS16 middle: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_keycap_in_middle():
    """Keycap in middle of phone."""
    value = '89174\u20e3005219'
    result = phone.analyze(RawCell(value))
    log(f'Keycap middle: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


if __name__ == '__main__':
    OUTPUT_FILE.write_text('', encoding='utf-8')
    test_devanagari_correct_digits()
    test_fullwidth_semicolon_vs_plus()
    test_emoji_after_phone()
    test_combining_mark_after_phone()
    test_variation_selector_after_phone()
    test_keycap_after_phone()
    test_emoji_before_phone()
    test_combining_mark_before_phone()
    test_variation_selector_before_phone()
    test_keycap_before_phone()
    test_emoji_in_middle_of_phone()
    test_combining_mark_in_middle()
    test_variation_selector_in_middle()
    test_keycap_in_middle()
    print(f'Results written to {OUTPUT_FILE}')
