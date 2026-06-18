from copy import deepcopy

from django.test import SimpleTestCase

from core.stage6_official_compatibility import (
    EXPECTED_DDJJ_MEDIA,
    build_stage6_official_compatibility_matrix,
    summarize_stage6_official_compatibility_for_presentation,
    validate_stage6_official_compatibility_matrix,
)
from sii.models import is_safe_public_sii_source_url


class Stage6OfficialCompatibilityTests(SimpleTestCase):
    def _row(self, matrix, key):
        return next(row for row in matrix['rows'] if row['key'] == key)

    def test_matrix_documents_f22_certification_without_content_certification(self):
        matrix = build_stage6_official_compatibility_matrix(anio_tributario=2026)
        self.assertEqual(validate_stage6_official_compatibility_matrix(matrix), [])

        row = self._row(matrix, 'f22_certification_2026')
        format_row = self._row(matrix, 'f22_record_format_2026')
        boundary = row['boundary']

        self.assertEqual(row['target_kind'], 'F22')
        self.assertIn(2025, matrix['supported_tax_years'])
        self.assertIn(2026, matrix['supported_tax_years'])
        self.assertIs(boundary['certified_file_path_exists'], True)
        self.assertIs(boundary['public_api_confirmed'], False)
        self.assertIs(boundary['content_consistency_certified'], False)
        self.assertIs(format_row['boundary']['fixed_width_record_contract_exists'], True)
        self.assertEqual(format_row['boundary']['record_length'], 90)
        self.assertEqual(set(format_row['boundary']['record_types']), {'0', '1'})
        self.assertIs(matrix['official_submission_allowed'], False)
        self.assertIs(matrix['final_tax_calculation'], False)

    def test_matrix_documents_ddjj_media_software_and_importer_paths(self):
        matrix = build_stage6_official_compatibility_matrix(anio_tributario=2026)

        media_row = self._row(matrix, 'ddjj_media_2026')
        software_row = self._row(matrix, 'ddjj_software_houses_2026')
        importer_row = self._row(matrix, 'ddjj_importer_manual_2026')

        self.assertEqual(set(media_row['supported_media']), EXPECTED_DDJJ_MEDIA)
        self.assertIs(media_row['boundary']['requires_form_specific_media'], True)
        self.assertIs(software_row['boundary']['commercial_software_file_path_exists'], True)
        self.assertIs(importer_row['boundary']['file_importer_path_exists'], True)
        self.assertIs(importer_row['boundary']['public_api_confirmed'], False)

    def test_matrix_covers_at2025_without_inventing_f22_fixed_width_format(self):
        matrix = build_stage6_official_compatibility_matrix(anio_tributario=2025)

        self.assertEqual(validate_stage6_official_compatibility_matrix(matrix), [])
        self.assertEqual(matrix['schema_version'], 'stage6-official-compatibility-at2025-at2026-v1')

        f22_row = self._row(matrix, 'f22_certification_2025')
        ddjj_process = self._row(matrix, 'ddjj_certification_process_2025')
        known_gap = next(gap for gap in matrix['known_gaps'] if gap['key'] == 'f22_record_format_2025')

        self.assertEqual(f22_row['source_url'], 'https://www.sii.cl/noticias/2025/120225noti01aav.htm')
        self.assertIs(f22_row['boundary']['certified_file_path_exists'], True)
        self.assertIs(f22_row['boundary']['public_api_confirmed'], False)
        self.assertIs(ddjj_process['boundary']['file_upload_certification_path_exists'], True)
        self.assertIs(ddjj_process['boundary']['production_environment_warning'], True)
        self.assertEqual(known_gap['status'], 'not_confirmed_from_public_source')
        self.assertIs(known_gap['required_before_official_f22_file'], True)

    def test_matrix_accepts_public_sii_alerce_sources(self):
        self.assertTrue(is_safe_public_sii_source_url('https://alerce.sii.cl/dior/dej/html/dj_autoverificacion.html'))
        self.assertTrue(is_safe_public_sii_source_url('https://alerce.sii.cl/dior/dej/html/manual/DJ_Manual/01.html'))
        self.assertTrue(is_safe_public_sii_source_url('https://alerce.sii.cl/dior/dej/pdf/Procedimiento_de_Revision_AT2025.pdf'))

        matrix = build_stage6_official_compatibility_matrix(anio_tributario=2026)
        self.assertEqual(validate_stage6_official_compatibility_matrix(matrix), [])

    def test_matrix_rejects_public_api_assumption_without_official_evidence(self):
        matrix = deepcopy(build_stage6_official_compatibility_matrix(anio_tributario=2026))
        matrix['rows'][0]['boundary']['public_api_confirmed'] = True

        issues = validate_stage6_official_compatibility_matrix(matrix)

        self.assertIn('f22_certification_2026.public_api_without_safe_evidence', issues)
        self.assertIn('f22_certification_2026.public_api_must_not_be_confirmed', issues)

    def test_matrix_rejects_any_attempt_to_enable_submission_or_final_calculation(self):
        matrix = deepcopy(build_stage6_official_compatibility_matrix(anio_tributario=2026))
        matrix['official_submission_allowed'] = True
        matrix['rows'][0]['boundary']['final_tax_calculation'] = True
        matrix['rows'][0]['boundary']['content_consistency_certified'] = True

        issues = validate_stage6_official_compatibility_matrix(matrix)

        self.assertIn('official_submission_must_remain_blocked', issues)
        self.assertIn('f22_certification_2026.final_tax_calculation_must_not_be_enabled', issues)
        self.assertIn('f22_certification_2026.content_consistency_must_not_be_certified_by_sii_file_gate', issues)

    def test_matrix_rejects_at2025_missing_explicit_f22_format_gap(self):
        matrix = deepcopy(build_stage6_official_compatibility_matrix(anio_tributario=2025))
        matrix['known_gaps'] = []

        issues = validate_stage6_official_compatibility_matrix(matrix)

        self.assertIn('f22_record_format_2025_missing_or_gap_not_explicit', issues)

    def test_matrix_rejects_unsupported_tax_year(self):
        matrix = build_stage6_official_compatibility_matrix(anio_tributario=2024)

        issues = validate_stage6_official_compatibility_matrix(matrix)

        self.assertIn('unsupported_tax_year', issues)

    def test_presentation_summary_blocks_at2025_until_f22_record_format_is_confirmed(self):
        summary = summarize_stage6_official_compatibility_for_presentation(anio_tributario=2025)

        self.assertFalse(summary['ready_for_controlled_presentation_approval'])
        self.assertEqual(summary['issue_codes'], [])
        self.assertIn('f22_record_format_2025', summary['known_gap_keys'])
        self.assertIn('f22_record_format_2025', summary['blocking_gap_keys'])
        self.assertFalse(summary['official_submission_allowed'])
        self.assertFalse(summary['final_tax_calculation'])

    def test_presentation_summary_allows_at2026_only_as_controlled_review_gate(self):
        summary = summarize_stage6_official_compatibility_for_presentation(anio_tributario=2026)

        self.assertTrue(summary['ready_for_controlled_presentation_approval'])
        self.assertEqual(summary['issue_codes'], [])
        self.assertEqual(summary['blocking_gap_keys'], [])
        self.assertFalse(summary['official_submission_allowed'])
        self.assertFalse(summary['public_api_general_available'])
        self.assertFalse(summary['final_tax_calculation'])
