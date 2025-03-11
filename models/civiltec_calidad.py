from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import namedtuple

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


from odoo import models, fields, api

class QualityFormInstance(models.Model):
    _name = 'quality.form.instance'
    _description = 'Encuestas de Calidad'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Enables chatter and activity tracking

    name = fields.Char(
        "Nombre de la Encuesta",
        compute="_compute_form_instance_name",
        store=True,
        tracking=True  # Track changes in chatter
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

    def action_en_proceso(self):
        self.state = 'en_proceso'

    def action_en_revision(self):
        self.state = 'en_revision'

    def action_realizado(self):
        self.state = 'realizado'

    def action_cancelar(self):
        self.state = 'cancelado'

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



class QualityFormResponse(models.Model):
    _name = 'quality.form.response'
    _description = 'Respuestas de Encuestas'

    state = fields.Selection([
        ('borrador', 'Borrador'),
        ('en_proceso', 'En proceso'),
        ('en_revision', 'Enviar para revisión'),
        ('realizado', 'Realizado'),
        ('cancelado', 'Cancelado'),
    ], string="Estado", default='borrador')


    def action_en_proceso(self):
        self.state = 'en_proceso'

    def action_en_revision(self):
        self.state = 'en_revision'

    def action_realizado(self):
        self.state = 'realizado'

    def action_cancelar(self):
        self.state = 'cancelado'

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
