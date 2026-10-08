"""Independent expectations: agent reproductions and approved spec 1.5 boundaries."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResourceCase:
    ident: str
    field_name: str
    value: object
    canonical: str | None
    codes: tuple = ()
    kwargs: dict = field(default_factory=dict)
    category: str = 'regression'


CASES = [
    ResourceCase('OC-SEMICOLON', 'phone', '；７９１７４００５２１９', '+79174005219', ('PHONE_EXTRA_CONTEXT',), category='oracle_correction'),
    ResourceCase('OC-INTERNAL-EMOJI', 'phone', '89174📞005219', None, ('PHONE_INVALID',)),
    ResourceCase('OC-LEADING-EMOJI', 'phone', '📞89174005219', '+79174005219', ('PHONE_EXTRA_CONTEXT',), category='oracle_correction'),
    ResourceCase('OC-TRAILING-EMOJI', 'phone', '89174005219📞', '+79174005219', ('PHONE_EXTRA_CONTEXT',), category='oracle_correction'),
    ResourceCase('OC-MARK-END', 'phone', '89174005219\u0301', None, ('PHONE_INVALID',)),
    ResourceCase('OC-MARK-START', 'phone', '\u030189174005219', None, ('PHONE_INVALID',)),
    ResourceCase('OC-VS-END', 'phone', '89174005219\ufe0f', None, ('PHONE_INVALID',)),
    ResourceCase('OC-KEYCAP-INTERNAL', 'phone', '89174\u20e3005219', None, ('PHONE_INVALID',)),
    ResourceCase('MARK-CONTEXT', 'phone', 'кафе\u0301: 89174005219', '+79174005219', ('PHONE_EXTRA_CONTEXT',)),
    ResourceCase('OC-NBSP-DATE', 'dates', '09\u202f03\u202f2026', '2026-03-09', category='approved_extension'),
    ResourceCase('OC-NBSP-AROUND-SLASH', 'dates', '09\u202f/\u202f03\u202f/\u202f2026', '2026-03-09'),
    ResourceCase('SPACE-YMD', 'dates', '2026\u00a009\u00a006', '2026-09-06', category='approved_extension'),
    ResourceCase('SPACE-MDY', 'dates', '09 25 2026', '2026-09-25', category='approved_extension'),
    ResourceCase('SPACE-NOT-EXISTING', 'dates', '31 02 2026', None, ('DATE_INVALID',), category='approved_extension'),
    ResourceCase('SPACE-MULTIPLE', 'dates', '09 03 2026; 25 09 2026', None, ('DATE_MULTIPLE',), category='approved_extension'),
    ResourceCase('SPACED-SLASH-MULTIPLE', 'dates', '09 / 03 / 2026; 25 / 09 / 2026', None, ('DATE_MULTIPLE',)),
    ResourceCase('GR-EXT-OTHER', 'phone', '+79174005219 доб. 917-400-52-20', None, ('PHONE_MULTIPLE',)),
    ResourceCase('EXT-HIDDEN-00', 'phone', '+79174005219 доб. 00-12-34-56-78', None, ('PHONE_UNSUPPORTED_PREFIX',)),
    ResourceCase('EXT-HIDDEN-810', 'phone', '+79174005219 доб. 810-123-45-678', None, ('PHONE_UNSUPPORTED_PREFIX',)),
    ResourceCase('GR-EXT-SAME', 'phone', '+79174005219 доб. 917-400-52-19', '+79174005219', ('PHONE_EXTRA_CONTEXT',), category='oracle_correction'),
    ResourceCase('GR-EXT-EMPTY', 'phone', '+79174005219 доб.', None, ('PHONE_INVALID',)),
    ResourceCase('GR-EXT-LETTERS', 'phone', '+79174005219 #abc', None, ('PHONE_INVALID',)),
    ResourceCase('GR-EXT-MARKED-WORD', 'phone', '+79174005219 вн. офис', None, ('PHONE_INVALID',)),
    ResourceCase('GR-EXT-RANGES', 'phone', '+74955878889, доб. 10-17, 10-13', '+74955878889', ('PHONE_EXTRA_CONTEXT',)),
    ResourceCase('GR-YEAR-MONTH', 'dates', '2026-09', None, ('DATE_INCOMPLETE',)),
    ResourceCase('GR-YEAR-MONTH-SLASH', 'dates', '2026/09', None, ('DATE_INCOMPLETE',)),
    ResourceCase('GR-FULL-MONTH-AFTER-H', 'dates', 46271, '2026-09-06', kwargs={'kind':'n', 'number_format':'h:mmmm d yyyy'}),
    ResourceCase('GR-FULL-MONTH-BEFORE-S', 'dates', 46271, '2026-09-06', kwargs={'kind':'n', 'number_format':'d yyyy mmmm:ss'}),
    ResourceCase('MINUTES-NOT-MONTH', 'dates', 46271, None, ('DATE_INCOMPLETE',), {'kind':'n', 'number_format':'dd yyyy hh:mm'}),
    ResourceCase('REAL-PREFIX-00', 'phone', '00339174005219', None, ('PHONE_UNSUPPORTED_PREFIX',)),
    ResourceCase('REAL-PREFIX-810', 'phone', '81012345678', None, ('PHONE_UNSUPPORTED_PREFIX',)),
    ResourceCase('REAL-FOREIGN-PLUS', 'phone', '+449174📞005219', None, ('PHONE_UNSUPPORTED_PREFIX',)),
    ResourceCase('LONG-DIGITS', 'phone', '89174005219123', None, ('PHONE_INVALID',)),
    ResourceCase('GROK-NO-FIRST', 'names', 'Волков Андреевич', None, ('NAME_AMBIGUOUS',), category='oracle_correction'),
]
