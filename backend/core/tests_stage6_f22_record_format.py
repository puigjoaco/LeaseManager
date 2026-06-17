from copy import deepcopy

from django.test import SimpleTestCase

from core.stage6_f22_record_format import (
    F22_RECORD_FORMAT_SOURCE_URL,
    F22_RECORD_LENGTH,
    build_f22_record_format_contract,
    build_f22_type0_record,
    build_f22_type1_record,
    validate_f22_fixed_width_record,
    validate_f22_record_format_contract,
)
from sii.models import is_safe_public_sii_source_url


class Stage6F22RecordFormatTests(SimpleTestCase):
    def test_contract_covers_sii_fixed_width_type0_and_type1_records(self):
        contract = build_f22_record_format_contract(anio_tributario=2026)

        self.assertEqual(validate_f22_record_format_contract(contract), [])
        self.assertEqual(contract['record_length'], F22_RECORD_LENGTH)
        self.assertEqual(contract['records']['0']['fields'][0]['required_value'], '0')
        self.assertEqual(contract['records']['0']['fields'][2]['required_value'], '0022')
        self.assertEqual(contract['records']['1']['fields'][0]['required_value'], '1')
        self.assertEqual(contract['records']['1']['fields'][-1]['start'], 82)
        self.assertEqual(contract['records']['1']['fields'][-1]['end'], 90)
        self.assertFalse(contract['boundary']['official_submission_allowed'])
        self.assertFalse(contract['boundary']['final_tax_calculation'])

    def test_contract_uses_public_sii_format_source(self):
        self.assertTrue(is_safe_public_sii_source_url(F22_RECORD_FORMAT_SOURCE_URL))

        contract = build_f22_record_format_contract(anio_tributario=2026)

        self.assertEqual(contract['source_url'], F22_RECORD_FORMAT_SOURCE_URL)
        self.assertEqual(validate_f22_record_format_contract(contract), [])

    def test_contract_rejects_submission_or_final_calculation_boundary_break(self):
        contract = deepcopy(build_f22_record_format_contract(anio_tributario=2026))
        contract['boundary']['official_submission_allowed'] = True
        contract['boundary']['final_tax_calculation'] = True

        issues = validate_f22_record_format_contract(contract)

        self.assertIn('official_submission_must_remain_blocked', issues)
        self.assertIn('final_tax_calculation_must_remain_blocked', issues)

    def test_type0_builder_emits_valid_90_character_header_record(self):
        line = build_f22_type0_record(
            anio_tributario=2026,
            rut_number='11111111',
            rut_dv='1',
            total_records=2,
            company_code='QA',
            client_number='123456',
            declarant_checksum=0,
        )

        self.assertEqual(len(line), 90)
        self.assertEqual(line[:9], '020260022')
        self.assertEqual(line[41:51], '0000000000')
        self.assertEqual(validate_f22_fixed_width_record(line), [])

    def test_type1_builder_emits_four_code_slots_and_filler(self):
        line = build_f22_type1_record(
            [
                {'code': '0001', 'sign': '+', 'value': '12345'},
                {'code': '0002', 'sign': '-', 'value': '678'},
            ]
        )

        self.assertEqual(len(line), 90)
        self.assertEqual(line[0], '1')
        self.assertEqual(line[1:5], '0001')
        self.assertEqual(line[21:25], '0002')
        self.assertEqual(line[61:65], '0000')
        self.assertEqual(line[81:90], ' ' * 9)
        self.assertEqual(validate_f22_fixed_width_record(line), [])

    def test_validator_rejects_wrong_length_unknown_type_and_type0_constants(self):
        self.assertEqual(validate_f22_fixed_width_record('0'), ['length_mismatch:1'])
        self.assertEqual(validate_f22_fixed_width_record('9' + ('0' * 89)), ['unknown_record_type:9'])

        line = build_f22_type0_record(
            anio_tributario=2026,
            rut_number='11111111',
            rut_dv='1',
            total_records=2,
            company_code='QA',
            client_number='123456',
        )
        tampered = line[:5] + '0023' + line[9:]

        self.assertIn('form_number.required_value_mismatch', validate_f22_fixed_width_record(tampered))
