from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import namedtuple
from odoo.exceptions import ValidationError

class QualityFormTemplate(models.Model):
    _name = 'quality.form.template'
    _description = 'Plantillas de Encuestas de Calidad'

    name = fields.Char("Nombre de la Plantilla", required=True)
    description = fields.Text("Descripción de la Plantilla")
    question_ids = fields.One2many(
        'quality.form.question',
        'form_template_id',
        string="Preguntas"
    )
    allow_multiple_properties = fields.Boolean(
        "Permitir selección de múltiples Propiedades",
        default=False,
        help="Si se activa, en las encuestas se podrá seleccionar más de una propiedad."
    )


class QualityFormQuestion(models.Model):
    _name = 'quality.form.question'
    _description = 'Preguntas de Calidad'

    name = fields.Char("Pregunta", required=True)
    form_template_id = fields.Many2one(
        'quality.form.template',
        string="Plantilla de Formulario",
        required=True,
        ondelete='cascade'
    )
    question_type = fields.Selection([
        ('text', 'Texto'),
        ('number', 'Número'),
        ('boolean', 'Sí/No'),
        ('date', 'Fecha'),
    ], string="Tipo de Pregunta", default='text')


class QualityFormInstance(models.Model):
    _name = 'quality.form.instance'
    _description = 'Encuestas de Calidad'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        "Nombre de la Encuesta",
        compute="_compute_form_instance_name",
        store=True,
        tracking=True
    )
    form_template_id = fields.Many2one(
        'quality.form.template',
        string="Plantilla de Formulario",
        required=True,
        tracking=True
    )
    property_id = fields.Many2one(
        'product.product',
        string="Propiedad",
        required=True,
        domain=[('is_property', '=', True)],
        tracking=True
    )

    property_ids = fields.Many2many(
        'product.product',
        string="Propiedades",
        domain=[('is_property', '=', True)],
        tracking=True
    )

     # Related field to show if multiple properties are allowed
    allow_multiple_properties = fields.Boolean(
        related='form_template_id.allow_multiple_properties',
        store=True,
        string="Permitir Múltiples Propiedades"
    )

    response_ids = fields.One2many(
        'quality.form.response',
        'form_instance_id',
        string="Respuestas"
    )

    state = fields.Selection([
        ('borrador', 'Borrador'),
        ('en_proceso', 'En proceso'),
        ('en_revision', 'Enviar para revisión'),
        ('realizado', 'Realizado'),
        ('cancelado', 'Cancelado'),
    ], string="Estado", default='borrador', tracking=True)

    # ----------------------------------------------------------
    # Transitions / Buttons
    # ----------------------------------------------------------

    def action_en_proceso(self):
        """
        Validations before setting the record to 'en_proceso'.
        """
        # Example: ensure there's at least one response
        if not self.response_ids:
            raise ValidationError(_("No hay respuestas, no se puede pasar a 'En proceso'."))

        # If all checks pass:
        self.state = 'en_proceso'

    def action_en_revision(self):
        """
        Validations before setting the record to 'en_revision'.
        Example: require every response to be filled if the question type demands it.
        """
        for line in self.response_ids:
            # Suppose we want to ensure that 'answer_text' is filled for text questions,
            # 'answer_number' for number questions, etc.
            if line.question_id.question_type == 'text' and not line.answer_text:
                raise ValidationError(_(
                    "Debes responder la pregunta '%s' con texto antes de enviar a revisión."
                ) % line.question_text)

            if line.question_id.question_type == 'number' and not line.answer_number:
                raise ValidationError(_(
                    "Debes responder la pregunta '%s' con un número antes de enviar a revisión."
                ) % line.question_text)

            # You can add more checks for 'boolean' or 'date' if needed.

        # If all checks pass:
        self.state = 'en_revision'

    def action_realizado(self):
        """
        Validations before marking the record as 'realizado'.
        Example: ensure that the user has not left any question blank or incomplete.
        """
        # Maybe you require that absolutely all fields (text, number, etc.) are filled
        # or any custom logic you need:
        for line in self.response_ids:
            if line.question_id.question_type in ('text', 'number') and not line.answer_text and not line.answer_number:
                raise ValidationError(_(
                    "La pregunta '%s' no está completamente respondida. Completa todas las respuestas antes de finalizar."
                ) % line.question_text)

        # If all checks pass:
        self.state = 'realizado'

    def action_cancelar(self):
        """
        Validation before canceling the record, if needed.
        """
        # Example: check if user is sure or if certain conditions must be met
        self.state = 'cancelado'

    # ----------------------------------------------------------
    # Compute & Onchange
    # ----------------------------------------------------------
    @api.depends('form_template_id', 'property_id')
    def _compute_form_instance_name(self):
        """Calcula el nombre de la encuesta combinando la plantilla y la propiedad."""
        for record in self:
            record.name = f'{record.form_template_id.name} - {record.property_id.name}'

    @api.onchange('form_template_id')
    def _onchange_form_template_id(self):
        """Rellena response_ids cuando se asigne form_template_id."""
        if self.form_template_id:
            question_ids = self.form_template_id.question_ids
            response_data = []
            for question in question_ids:
                response_data.append((0, 0, {
                    'question_id': question.id,
                }))
            self.response_ids = response_data  # Asigna valores por defecto

    def unlink(self):
        """Only allow deletion if the record is in 'borrador' state."""
        for record in self:
            if record.state != 'borrador':
                raise ValidationError("Solo se pueden eliminar registros en estado 'Borrador'.")
        return super(QualityFormInstance, self).unlink()



class QualityFormResponse(models.Model):
    _name = 'quality.form.response'
    _description = 'Respuestas de Encuestas'

    question_id = fields.Many2one(
        'quality.form.question',
        string="Pregunta",
        required=True
    )
    question_text = fields.Char(
        related='question_id.name',
        string="Texto de la Pregunta",
        store=True
    )
    form_instance_id = fields.Many2one(
        'quality.form.instance',
        string="Encuesta",
        required=True,
        ondelete='cascade'
    )
    answer_text = fields.Char("Respuesta (Texto)")
    answer_number = fields.Float("Respuesta (Número)")
    answer_boolean = fields.Boolean("Respuesta (Sí/No)")
    answer_date = fields.Date("Respuesta (Fecha)")

    @api.onchange('question_id')
    def _onchange_question_type(self):
        """Limpia los campos de respuesta si se selecciona otra pregunta."""
        if self.question_id:
            self.answer_text = False
            self.answer_number = False
            self.answer_boolean = False
            self.answer_date = False
            # Restringir domain de question_id a solo preguntas de la plantilla de la encuesta
            return {
                'domain': {
                    'question_id': [
                        ('form_template_id', '=', self.form_instance_id.form_template_id.id)
                    ]
                }
            }
