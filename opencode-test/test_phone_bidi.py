"""Bidi override attacks and Unicode edge cases in phone analysis."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from normalizer import phone
from normalizer.models import RawCell

OUTPUT_FILE = Path(__file__).parent / 'bidi_results.txt'


def log(message):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(message + '\n')


def test_bidi_override_hidden_digits():
    """Bidi RLO/LRO/PDF can hide digits or change phone meaning visually."""
    value = '\u202e89174005219\u202c'
    result = phone.analyze(RawCell(value))
    log(f'Bidi RLO: input={repr(value)}, canonical={result.canonical}, codes={result.codes}, display={repr(result.display)}')


def test_bidi_with_mixed_digits():
    """Bidi controls mixed with actual digits."""
    value = '+\u202e7917\u202c4005219'
    result = phone.analyze(RawCell(value))
    log(f'Bidi mixed: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_zwj_zwnj_in_phone():
    """Zero-width joiner/non-joiner inside phone number."""
    value = '8\u200d9174005219'
    result = phone.analyze(RawCell(value))
    log(f'ZWJ: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')

    value2 = '8\u200c9174005219'
    result2 = phone.analyze(RawCell(value2))
    log(f'ZWNJ: input={repr(value2)}, canonical={result2.canonical}, codes={result2.codes}')


def test_soft_hyphen_in_phone():
    """Soft hyphen (U+00AD) inside phone number."""
    value = '8\xad9174005219'
    result = phone.analyze(RawCell(value))
    log(f'Soft hyphen: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_narrow_no_break_space_separator():
    """Narrow no-break space (U+202F) as phone separator."""
    value = '8\u202f917\u202f400\u202f52\u202f19'
    result = phone.analyze(RawCell(value))
    log(f'Narrow NBSP: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_mongolian_vowel_separator():
    """Mongolian vowel separator (U+180E)."""
    value = '8\u180e9174005219'
    result = phone.analyze(RawCell(value))
    log(f'MVS: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_tag_characters_in_phone():
    """Unicode tag characters (U+E0000 block)."""
    value = '8\U000e00019174005219'
    result = phone.analyze(RawCell(value))
    log(f'Tag char: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_arabic_indic_digits_ru():
    """Arabic-Indic digits should be converted via unicodedata.decimal (Nd category)."""
    value = '\u0668\u0669\u0661\u0667\u0664\u0660\u0660\u0665\u0662\u0661\u0669'
    result = phone.analyze(RawCell(value))
    log(f'Arabic-Indic: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_devanagari_digits():
    """Devanagari digits."""
    value = '\u0968\u0969\u0967\u0966\u096a\u0966\u0966\u0966\u0968\u0967\u0969'
    result = phone.analyze(RawCell(value))
    log(f'Devanagari: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_fullwidth_plus_and_digits():
    """Fullwidth plus sign and fullwidth digits."""
    value = '\uff1b\uff17\uff19\uff11\uff17\uff14\uff10\uff10\uff15\uff12\uff11\uff19'
    result = phone.analyze(RawCell(value))
    log(f'Fullwidth: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_phone_with_emoji():
    """Phone with emoji."""
    value = '89174005219\U0001f4de'
    result = phone.analyze(RawCell(value))
    log(f'Emoji: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_phone_with_combining_marks():
    """Phone with combining diacritical marks."""
    value = '89174005219\u0301'
    result = phone.analyze(RawCell(value))
    log(f'Combining: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_phone_with_variation_selector():
    """Phone with variation selector (U+FE0F)."""
    value = '89174005219\ufe0f'
    result = phone.analyze(RawCell(value))
    log(f'VS: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_phone_with_byte_order_mark():
    """BOM (U+FEFF) at start of phone."""
    value = '\ufeff89174005219'
    result = phone.analyze(RawCell(value))
    log(f'BOM: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


def test_phone_with_enclosing_mark():
    """Phone with enclosing keycap mark (U+20E3)."""
    value = '89174005219\u20e3'
    result = phone.analyze(RawCell(value))
    log(f'Keycap: input={repr(value)}, canonical={result.canonical}, codes={result.codes}')


if __name__ == '__main__':
    OUTPUT_FILE.write_text('', encoding='utf-8')
    test_bidi_override_hidden_digits()
    test_bidi_with_mixed_digits()
    test_zwj_zwnj_in_phone()
    test_soft_hyphen_in_phone()
    test_narrow_no_break_space_separator()
    test_mongolian_vowel_separator()
    test_tag_characters_in_phone()
    test_arabic_indic_digits_ru()
    test_devanagari_digits()
    test_fullwidth_plus_and_digits()
    test_phone_with_emoji()
    test_phone_with_combining_marks()
    test_phone_with_variation_selector()
    test_phone_with_byte_order_mark()
    test_phone_with_enclosing_mark()
    print(f'Results written to {OUTPUT_FILE}')
