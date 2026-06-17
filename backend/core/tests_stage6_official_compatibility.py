from copy import deepcopy

from django.test import SimpleTestCase

from core.stage6_official_compatibility import (
    EXPECTED_DDJJ_MEDIA,
    build_stage6_official_compatibility_matrix,
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
        importer_row = self._row(matrix, 'ddjj_importer_manual')

        self.assertEqual(set(media_row['supported_media']), EXPECTED_DDJJ_MEDIA)
        self.assertIs(media_row['boundary']['requires_form_specific_media'], True)
        self.assertIs(software_row['boundary']['commercial_software_file_path_exists'], True)
        self.assertIs(importer_row['boundary']['file_importer_path_exists'], True)
        self.assertIs(importer_row['boundary']['public_api_confirmed'], False)

    def test_matrix_accepts_public_sii_alerce_sources(self):
        self.assertTrue(is_safe_public_sii_source_url('https://alerce.sii.cl/dior/dej/html/dj_autoverificacion.html'))
        self.assertTrue(is_safe_public_sii_source_url('https://alerce.sii.cl/dior/dej/html/manual/DJ_Manual/01.html'))

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
