# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Archivos adjuntos a documentos de QSG: solo imágenes reales y de tamaño acotado.

Se revisa el contenido (los primeros bytes), no la extensión ni el tipo que declara el
navegador: un .html o un .svg con script, o un ejecutable renombrado a .jpg, se rechazan.
"""

import frappe
from frappe.core.doctype.file.file import File
from frappe.utils import cint

from qsg_pmo.seguridad.eventos import registrar

QSG_DOCTYPES_PREFIX = "QSG "
DEFAULT_MAX_MB = 10
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "heic", "heif", "pdf"}


def detectar_tipo(content: bytes) -> str | None:
	"""Tipo real del archivo por su firma binaria."""
	head = content[:16]
	if head.startswith(b"\xff\xd8\xff"):
		return "jpg"
	if head.startswith(b"\x89PNG\r\n\x1a\n"):
		return "png"
	if head[:4] == b"RIFF" and content[8:12] == b"WEBP":
		return "webp"
	if content[4:8] == b"ftyp" and content[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"hevc", b"heif"):
		return "heic"
	if head.startswith(b"%PDF-"):
		return "pdf"
	return None


def max_bytes() -> int:
	try:
		mb = cint(frappe.db.get_single_value("QSG Configuracion", "max_photo_mb")) or DEFAULT_MAX_MB
	except Exception:
		mb = DEFAULT_MAX_MB
	return mb * 1024 * 1024


def validar_contenido(
	content: bytes, filename: str, reference_doctype=None, reference_name=None, solo_imagen=True
):
	"""Lanza un error (y lo registra) si el archivo no es aceptable. Devuelve el tipo real."""
	limit = max_bytes()
	if len(content) > limit:
		_rechazar(
			f"El archivo pesa {len(content) // 1024} KB; el máximo es {limit // 1048576} MB.",
			filename,
			reference_doctype,
			reference_name,
		)
	kind = detectar_tipo(content)
	allowed = {"jpg", "png", "webp", "heic"} if solo_imagen else {"jpg", "png", "webp", "heic", "pdf"}
	if kind not in allowed:
		_rechazar(
			"Solo se aceptan fotos (JPG, PNG, WEBP o HEIC).", filename, reference_doctype, reference_name
		)
	ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
	if ext and ext not in ALLOWED_EXT:
		_rechazar("Extensión de archivo no permitida.", filename, reference_doctype, reference_name)
	return kind


def _rechazar(message, filename, reference_doctype, reference_name):
	registrar("Archivo rechazado", f"{message} Archivo: {filename}", reference_doctype, reference_name)
	frappe.throw(message, frappe.ValidationError)


def _revisar(doc):
	if not (doc.attached_to_doctype or "").startswith(QSG_DOCTYPES_PREFIX) or not doc.attached_to_name:
		return
	if doc.is_folder or doc.flags.copy_from_existing_file or (doc.file_url or "").startswith("http"):
		return
	try:
		content = doc.get_content()
	except Exception:
		content = b""
	if isinstance(content, str):
		content = content.encode()
	validar_contenido(
		content or b"",
		doc.file_name or doc.file_url or "",
		doc.attached_to_doctype,
		doc.attached_to_name,
		solo_imagen=False,
	)


class ArchivoQSG(File):
	"""File con la revisión hecha *antes* de que Frappe procese el contenido.

	Frappe guarda el archivo en disco y le quita los metadatos EXIF dentro de su propio
	``before_insert``; si el contenido no es una imagen eso termina en un error 500 sin
	registro. Revisando primero, el rechazo es limpio (417) y queda en el registro.
	"""

	def before_insert(self):
		_revisar(self)
		super().before_insert()


def on_file_insert(doc, method=None):
	"""Hook de File (segunda revisión, con el contenido ya guardado).

	Si se rechaza, Frappe borra el archivo del disco al deshacer la transacción.
	"""
	_revisar(doc)
