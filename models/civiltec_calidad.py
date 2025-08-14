from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import namedtuple
from odoo.exceptions import ValidationError

class QualityFormTemplate(models.Model):
    _name = 'quality.form.template'
    _description = 'Plantillas de Formulario de Calidad'

    default_responsable_user_id = fields.Many2one(
        'res.users',
        string="Ingeniero Responsable por Defecto"
    )
    name = fields.Char("Nombre del Formulario Estándar", required=True)
    description = fields.Text("Descripción")
    company_id = fields.Many2one(
        'res.company',
        string="Empresa",
        required=True,
        default=lambda self: self.env.company
    )
    question_ids = fields.One2many(
        'quality.form.question',
        'form_template_id',
        string="Ítems de Revisión"
    )
    allow_multiple_properties = fields.Boolean(
        "¿Aplicable a Múltiples Propiedades?",
        default=False,
        help="Si se activa, en las encuestas se podrá seleccionar más de una propiedad."
    )


class QualityFormQuestion(models.Model):
    _name = 'quality.form.question'
    _description = 'Preguntas de Calidad'

    name = fields.Char("Pregunta", required=True)
    form_template_id = fields.Many2one(
        'quality.form.template',
        string="Formulario Estándar Usado",
        required=True,
        ondelete='cascade'
    )
    question_type = fields.Selection([
        ('text', 'Detalle de Revisión'),
        ('boolean', 'Aprobado'),
        ('date', 'Fecha Revisión'),
    ], string="Tipo de Pregunta", default='text')


class QualityFormInstance(models.Model):
    _name = 'quality.form.instance'
    _description = 'Encuestas de Calidad'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one(
        'res.company',
        string="Empresa",
        required=True,
        default=lambda self: self.env.company
    )

    responsable_user_id = fields.Many2one(
        'res.users',
        string="Ingeniero Responsable",
        related='form_template_id.default_responsable_user_id',
        store=True,
        readonly=False
    )

    residente_user_id = fields.Many2one(
        'res.users',
        string="Ingeniero Residente"
    )

    name = fields.Char(
        "Referencia Revisión",
        compute="_compute_form_instance_name",
        store=True,
        tracking=True
    )
    form_template_id = fields.Many2one(
        'quality.form.template',
        string="Formulario Estándar Usado",
        required=True,
        tracking=True,
        domain="[('company_id', '=', company_id)]"
    )
    property_ids = fields.Many2many(
        'product.product',
        string="Propiedades",
        domain=[('is_property', '=', True)],
        tracking=True
    )
    allow_multiple_properties = fields.Boolean(
        related='form_template_id.allow_multiple_properties',
        store=True,
        string="Permitir Múltiples Propiedades"
    )
    response_ids = fields.One2many(
        'quality.form.response',
        'form_instance_id',
        string="Detalle de Revisión",
        tracking=True
    )
    state = fields.Selection([
        ('no_listo', 'No Listo'),
        ('en_revision', 'En Revisión Interna'),
        ('realizado', 'Aprobado'),
        ('cancelado', 'Cancelado'),
    ], string="Estado", default='no_listo', tracking=True)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        args = args or []
        args += [('company_id', '=', self.env.company.id)]
        return super()._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.depends('form_template_id', 'property_ids')
    def _compute_form_instance_name(self):
        """Calcula el Referencia Revisión combinando la plantilla y las propiedades."""
        for record in self:
            property_names = ', '.join(record.property_ids.mapped('name'))
            record.name = f'{record.form_template_id.name} - {property_names}'

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
            self.response_ids = response_data
    def _onchange_responsable_user_id(self):
        """Rellena responsable_user_id cuando se asigne responsable_user_id."""
        if self.responsable_user_id:
            self.responsable_user_id = self.responsable_user_id

    def _send_state_change_email(self):
        """Send an email notification using the defined template."""
        mail_template = self.env.ref('civiltec_calidad.email_template_quality_form_instance_state', raise_if_not_found=False)
        if mail_template:
            # Send the email using the record's id
            mail_template.send_mail(self.id, force_send=True)

    def action_en_revision(self):
        """
        Validations before setting the record to 'en_revision'.
        """
        for line in self.response_ids:
            if not line.answer_text and not line.answer_number and not line.answer_boolean and not line.answer_date:
                raise ValidationError(_(
                    "Debes responder la pregunta '%s' antes de enviar a revisión."
                ) % line.question_text)
        self.state = 'en_revision'
        self._send_state_change_email()

    def action_realizado(self):
        """
        Validations before marking the record as 'realizado'.
        """
        for line in self.response_ids:
            if line.question_id.question_type in ('text', 'number') and not line.answer_text and not line.answer_number:
                raise ValidationError(_(
                    "La pregunta '%s' no está completamente respondida. Completa todas las Detalle de Revisión antes de finalizar."
                ) % line.question_text)
        self.state = 'realizado'
        self._send_state_change_email()

    def action_cancelar(self):
        """
        Validation before canceling the record.
        """
        self.state = 'cancelado'
        self._send_state_change_email()

    # def unlink(self):
    #     """Only allow deletion if the record is in 'no listo' state."""
    #     for record in self:
    #         if record.state != 'no_listo':
    #             raise ValidationError(_("Solo se pueden eliminar registros en estado 'no listo'."))
    #     return super(QualityFormInstance, self).unlink()


class QualityFormResponse(models.Model):
    _name = 'quality.form.response'
    _description = 'Detalle de Revisión'

    question_id = fields.Many2one(
        'quality.form.question',
        string="Pregunta",
        required=True
    )
    question_text = fields.Char(
        related='question_id.name',
        string="Ítem de Revisión",
        store=True
    )
    form_instance_id = fields.Many2one(
        'quality.form.instance',
        string="Encuesta",
        required=True,
        ondelete='cascade'
    )
    answer_text = fields.Char("Detalle de Revisión", tracking=True)
    answer_number = fields.Float("Valor Registrado", tracking=True)
    answer_boolean = fields.Boolean("Aprobado" , tracking=True)
    answer_date = fields.Date("Fecha Revisión" , tracking=True)

    @api.model
    def create(self, vals):
        vals['answer_date'] = fields.Date.today()
        return super(QualityFormResponse, self).create(vals)

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
