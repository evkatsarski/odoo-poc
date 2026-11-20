from odoo.tests import TransactionCase, tagged
from odoo.tools.translate import code_translations


@tagged('post_install', '-at_install')
class TestLeatherLanguages(TransactionCase):

    def test_bulgarian_is_default_and_english_stays_available(self):
        installed = dict(self.env['res.lang'].get_installed())
        self.assertIn('bg_BG', installed)
        self.assertIn('en_US', installed)
        self.assertEqual(self.env['ir.default']._get('res.partner', 'lang'), 'bg_BG')
        self.assertEqual(self.env.company.partner_id.lang, 'bg_BG')
        for xmlid in (
            'leather_inspection.user_entry_a',
            'leather_inspection.user_entry_b',
            'leather_inspection.user_operator',
            'leather_inspection.user_admin',
        ):
            user = self.env.ref(xmlid)
            self.assertEqual(user.lang, 'bg_BG', xmlid)
            user.write({'lang': 'en_US'})
            self.assertEqual(user.lang, 'en_US')
            user.write({'lang': 'bg_BG'})

        menu = self.env.ref('leather_inspection.menu_leather_inspection_root')
        self.assertEqual(menu.with_context(lang='bg_BG').name, 'Инспекции на кожа')
        self.assertEqual(menu.with_context(lang='en_US').name, 'Leather Inspections')

        bg_state = self.env['leather.inspection'].with_context(lang='bg_BG').fields_get(['state'])['state']
        en_state = self.env['leather.inspection'].with_context(lang='en_US').fields_get(['state'])['state']
        self.assertEqual(dict(bg_state['selection'])['draft'], 'Чернова')
        self.assertEqual(dict(en_state['selection'])['draft'], 'Draft')

        translated = code_translations.get_python_translations('leather_inspection', 'bg_BG')
        self.assertEqual(
            translated['Grade is required before submission.'],
            'Класът е задължителен преди изпращане.',
        )
        self.assertEqual(
            code_translations.get_python_translations('leather_inspection', 'en_US').get(
                'Grade is required before submission.'
            ),
            None,
        )
