from odoo import models, fields, api,  _
from odoo.exceptions import UserError
from collections import namedtuple

# modelos de plataforma de arquitectura 


class QualityFormTemplate(models.Model):
    _name = 'quality.form.template'
    _description = 'Plantillas de Encuestas de calidad'

    name = fields.Char("Form Name", required=True)
    description = fields.Text("Form Description")
    question_ids = fields.One2many('quality.form.question', 'form_template_id', string="Questions")

class QualityFormQuestion(models.Model):
    _name = 'quality.form.question'
    _description = 'Preguntas de calidad'

    name = fields.Char("Question", required=True)
    form_template_id = fields.Many2one('quality.form.template', string="Form Template", required=True, ondelete='cascade')
    question_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Yes/No'),
        ('date', 'Date'),
    ], string="Question Type", default='text')

class QualityFormInstance(models.Model):
    _name = 'quality.form.instance'
    _description = 'Encuestas de Calidad'

    name = fields.Char("Form Instance", compute="_compute_form_instance_name", store=True)
    form_template_id = fields.Many2one('quality.form.template', string="Form Template", required=True)
    property_id = fields.Many2one('product.product', string="Property", required=True, domain=[('is_property', '=', True)])
    response_ids = fields.One2many('quality.form.response', 'form_instance_id', string="Responses")

    @api.depends('form_template_id', 'property_id')
    def _compute_form_instance_name(self):
        for record in self:
            record.name = f'{record.form_template_id.name} for {record.property_id.name}'

    @api.onchange('form_template_id')
    def _onchange_form_template_id(self):
        """ Populate response_ids when form_template_id is set """
        if self.form_template_id:
            question_ids = self.form_template_id.question_ids
            response_data = []
            for question in question_ids:
                response_data.append((0, 0, {
                    'question_id': question.id,
                }))
            self.response_ids = response_data  # Fill One2many field with default values

    def create(self, vals):
        """ Ensure questions are created when a new record is created """
        instance = super(QualityFormInstance, self).create(vals)
        if instance.form_template_id:
            question_ids = instance.form_template_id.question_ids
            response_data = [(0, 0, {'question_id': question.id}) for question in question_ids]
            instance.response_ids = response_data
        return instance

    def write(self, vals):
        """ Ensure that response_ids are updated if the form template changes """
        result = super(QualityFormInstance, self).write(vals)
        if 'form_template_id' in vals:
            for instance in self:
                question_ids = instance.form_template_id.question_ids
                response_data = [(0, 0, {'question_id': question.id}) for question in question_ids]
                instance.response_ids = response_data
        return result


class QualityFormResponse(models.Model):
    _name = 'quality.form.response'
    _description = 'Respuestas de encuestas'

    question_id = fields.Many2one('quality.form.question', string="Question", required=True)
    question_text = fields.Char(related='question_id.name', string="Question", store=True)
    form_instance_id = fields.Many2one('quality.form.instance', string="Form Instance", required=True, ondelete='cascade')
    answer_text = fields.Char("Answer (Text)", required=False)
    answer_number = fields.Float("Answer (Number)", required=False)
    answer_boolean = fields.Boolean("Answer (Yes/No)", required=False)
    answer_date = fields.Date("Answer (Date)", required=False)

    @api.onchange('question_id')
    def _onchange_question_type(self):
        if self.question_id:
            question_type = self.question_id.question_type
            self.answer_text = False
            self.answer_number = False
            self.answer_boolean = False
            self.answer_date = False
            # This controls what field becomes visible in the form view
            return {
                'domain': {'question_id': [('form_template_id', '=', self.form_instance_id.form_template_id.id)]}
            }

