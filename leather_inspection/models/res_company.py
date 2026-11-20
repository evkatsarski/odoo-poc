import base64

from odoo import api, models
from odoo.tools import file_open

KROY_NAME = 'KROY'
KROY_ESPRESSO = '#281C17'
KROY_OLIVE = '#596253'
KROY_LOGO = 'leather_inspection/static/src/img/kroy-mark.png'


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _kroy_apply_brand(self):
        """Name the prototype company and store the KROY mark as its logo.

        ``base.main_company`` is noupdate in Community, so a data record would
        not refresh the name or the logo on later module updates. This function
        runs from module data on install and on update. Login, reports, and the
        Enterprise home menu read ``res.company.logo``; they are not patched here.
        """
        company = self.env.ref('base.main_company', raise_if_not_found=False) or self.env.company
        company._kroy_write_brand()

    def _kroy_write_brand(self):
        with file_open(KROY_LOGO, 'rb') as handle:
            logo = base64.b64encode(handle.read()).decode()
        for company in self:
            company.write({
                'name': KROY_NAME,
                'logo': logo,
                'primary_color': KROY_ESPRESSO,
                'secondary_color': KROY_OLIVE,
            })
