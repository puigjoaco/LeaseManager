import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_load_plan import load_manifest_json
from core.annual_tax_ownership_candidate_review import review_annual_tax_ownership_candidates
from core.annual_tax_ownership_snapshot_template import build_annual_tax_ownership_snapshot_template
from core.annual_tax_ownership_visual_review_packet import build_annual_tax_ownership_visual_review_packet
from core.annual_tax_source_manifest import build_annual_tax_source_manifest, payload_hash


CHAIN_SCHEMA_VERSION = 'annual-tax-ownership-evidence-chain.v1'


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _local_evidence_root() -> Path:
    return (Path(settings.PROJECT_ROOT).resolve() / 'local-evidence').resolve()


def _default_output_dir(*, company_ref: str, commercial_year: int, tax_year: int, run_label: str) -> Path:
    return (
        _local_evidence_root()
        / company_ref
        / f'ac{commercial_year}-at{tax_year}'
        / f'ownership-evidence-chain-{run_label}'
    ).resolve()


def _validate_local_evidence_dir(path: Path) -> None:
    try:
        path.relative_to(_local_evidence_root())
    except ValueError as error:
        raise CommandError(
            'La cadena de evidencia ownership puede contener indices tributarios y '
            'imagenes sensibles; --output-dir debe quedar bajo local-evidence/.'
        ) from error


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding='utf-8')


def _repo_ref(path: Path) -> str:
    repo_root = Path(settings.PROJECT_ROOT).resolve()
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


class Command(BaseCommand):
    help = (
        'Regenera la cadena segura de evidencia ownership AC/AT: manifiesto, '
        'revision de candidatos, template controlado y paquete visual local.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--source-root', required=True, help='Carpeta externa a revisar en modo read-only.')
        parser.add_argument('--company-ref', required=True, help='Referencia no sensible de empresa.')
        parser.add_argument('--commercial-year', type=int, required=True, help='Ano comercial fuente.')
        parser.add_argument('--tax-year', type=int, default=None, help='Ano tributario destino. Default: commercial-year + 1.')
        parser.add_argument('--run-label', default='v1', help='Sufijo no sensible para nombres de salida.')
        parser.add_argument('--source-label', default='', help='source_label no sensible sugerido para AnnualTaxSourceBundle.')
        parser.add_argument(
            '--authorization-ref',
            default='user-authorized-local-source-review',
            help='authorization_ref no sensible para fuente snapshot/controlada.',
        )
        parser.add_argument(
            '--responsible-ref',
            default='codex-local-review',
            help='responsible_ref no sensible del responsable de revision.',
        )
        parser.add_argument(
            '--approval-ref',
            default='',
            help='Referencia no sensible de aprobacion para completar luego el template.',
        )
        parser.add_argument('--output-dir', default='', help='Directorio bajo local-evidence/. Default canonico por empresa/AC/AT.')
        parser.add_argument(
            '--f29-no-declaration-month',
            type=int,
            action='append',
            dest='f29_no_declaration_months',
            default=[],
            help='Mes AC sin F29 por ausencia declarada/registrada. Puede repetirse.',
        )
        parser.add_argument(
            '--skip-visual-review-packet',
            action='store_true',
            help='Omite render visual. Util para pruebas o entornos sin pdftoppm.',
        )
        parser.add_argument(
            '--fail-if-no-reviewable-candidate',
            action='store_true',
            help='Sale con error si no hay candidatos utiles para revision controlada.',
        )
        parser.add_argument(
            '--fail-if-no-render',
            action='store_true',
            help='Sale con error si el paquete visual no renderiza ninguna pagina.',
        )
        parser.add_argument('--max-pages-per-candidate', type=int, default=2)
        parser.add_argument('--resolution', type=int, default=150)

    def handle(self, *args, **options):
        company_ref = str(options['company_ref'])
        commercial_year = int(options['commercial_year'])
        tax_year = int(options.get('tax_year') or commercial_year + 1)
        run_label = str(options.get('run_label') or 'v1').strip() or 'v1'
        source_root = _resolve_path(options['source_root'])
        output_dir = (
            _resolve_path(options['output_dir'])
            if options.get('output_dir')
            else _default_output_dir(
                company_ref=company_ref,
                commercial_year=commercial_year,
                tax_year=tax_year,
                run_label=run_label,
            )
        )
        _validate_local_evidence_dir(output_dir)

        prefix = f'ac{commercial_year}_at{tax_year}_{run_label}'
        manifest_path = output_dir / f'annual_tax_source_manifest_{prefix}.json'
        review_path = output_dir / f'annual_tax_ownership_candidate_review_{prefix}.json'
        template_path = output_dir / f'annual_tax_ownership_snapshot_template_{prefix}.json'
        visual_dir = output_dir / f'ownership-visual-review-{run_label}'
        visual_path = output_dir / f'annual_tax_ownership_visual_review_packet_{prefix}.json'
        summary_path = output_dir / f'annual_tax_ownership_evidence_chain_{prefix}.json'

        try:
            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref=company_ref,
                commercial_year=commercial_year,
                tax_year=tax_year,
                source_label=options.get('source_label') or '',
                authorization_ref=options['authorization_ref'],
                responsible_ref=options['responsible_ref'],
                include_file_list=True,
                f29_no_declaration_months=options['f29_no_declaration_months'],
            )
            manifest = load_manifest_json(json.dumps(manifest, ensure_ascii=True))
            review = review_annual_tax_ownership_candidates(
                manifest=manifest,
                source_root=source_root,
                company_ref=company_ref,
                commercial_year=commercial_year,
                tax_year=tax_year,
            )
            template = build_annual_tax_ownership_snapshot_template(
                review=review,
                company_ref=company_ref,
                commercial_year=commercial_year,
                tax_year=tax_year,
                responsible_ref=options['responsible_ref'],
                approval_ref=options.get('approval_ref') or '',
            )
            visual_packet = None
            if not options['skip_visual_review_packet']:
                visual_packet = build_annual_tax_ownership_visual_review_packet(
                    manifest=manifest,
                    review=review,
                    source_root=source_root,
                    output_dir=visual_dir,
                    company_ref=company_ref,
                    commercial_year=commercial_year,
                    tax_year=tax_year,
                    max_pages_per_candidate=options['max_pages_per_candidate'],
                    resolution=options['resolution'],
                )
        except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError) as error:
            raise CommandError(f'Cadena ownership invalida: {error}') from error

        _write_json(manifest_path, manifest)
        _write_json(review_path, review)
        _write_json(template_path, template)
        if visual_packet is not None:
            _write_json(visual_path, visual_packet)

        artifacts = {
            'manifest': _repo_ref(manifest_path),
            'ownership_candidate_review': _repo_ref(review_path),
            'ownership_snapshot_template': _repo_ref(template_path),
        }
        if visual_packet is not None:
            artifacts['ownership_visual_review_packet'] = _repo_ref(visual_path)
            artifacts['ownership_visual_review_dir'] = _repo_ref(visual_dir)

        reviewable_candidates = review['summary']['candidate_for_controlled_snapshot_review_count'] + review[
            'summary'
        ]['manual_review_legal_candidate_count']
        summary = {
            'schema_version': CHAIN_SCHEMA_VERSION,
            'company_ref': company_ref,
            'commercial_year': commercial_year,
            'tax_year': tax_year,
            'run_label': run_label,
            'source_hash': payload_hash(
                {
                    'manifest_schema_version': manifest.get('schema_version'),
                    'manifest_hash': payload_hash(
                        {
                            'coverage': manifest.get('coverage'),
                            'file_count': manifest.get('file_count'),
                            'bundle_draft': manifest.get('bundle_draft'),
                        }
                    ),
                    'review_summary': review.get('summary'),
                    'template_decision': template.get('decision'),
                    'visual_summary': (visual_packet or {}).get('summary'),
                }
            ),
            'safety': {
                'writes_database': False,
                'copies_source_files': False,
                'stores_raw_text': False,
                'stores_rut_values': False,
                'stores_participant_names': False,
                'auto_generates_socios_or_percentages': False,
                'uses_sii_real': False,
                'uses_credentials': False,
                'outputs_under_local_evidence': True,
            },
            'artifacts': artifacts,
            'summary': {
                'ownership_source_present': manifest['coverage']['ownership_source_present'],
                'ownership_source_candidate_present': manifest['coverage']['ownership_source_candidate_present'],
                'candidate_files_total': review['summary']['candidate_files_total'],
                'reviewable_candidates_total': reviewable_candidates,
                'template_ready_for_manual_completion': template['decision'][
                    'can_patch_controlled_db_load_package_after_manual_completion'
                ],
                'visual_packet_generated': visual_packet is not None,
                'rendered_pages_total': (visual_packet or {}).get('summary', {}).get('rendered_pages_total', 0),
                'ready_for_controlled_db_load': False,
            },
            'next_actions': [
                'Revisar/OCR localmente los candidatos ownership si el paquete visual fue generado.',
                'Completar participants en el template solo desde fuente societaria suficiente.',
                'Ejecutar audit_annual_tax_controlled_package_readiness despues de inyectar ownership controlado.',
            ],
        }
        _write_json(summary_path, summary)

        if options['fail_if_no_reviewable_candidate'] and not reviewable_candidates:
            raise CommandError('No hay candidatos ownership revisables para completar el template.')
        if options['fail_if_no_render'] and not summary['summary']['rendered_pages_total']:
            raise CommandError('No se renderizo ninguna pagina de candidatos ownership.')

        self.stdout.write(json.dumps(summary, ensure_ascii=True))
