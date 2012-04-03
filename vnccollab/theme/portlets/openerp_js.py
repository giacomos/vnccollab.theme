import re
import xmlrpclib
from urlparse import urlparse, parse_qs

from zope.formlib import form
from zope.interface import implements, Interface
from zope.component import getUtility
from zope import schema
from zope.annotation.interfaces import IAnnotations, IAttributeAnnotatable

from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode

from plone.memoize.instance import memoize
from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base

from vnccollab.theme import messageFactory as _


class IOpenERPJSPortlet(IPortletDataProvider):
    header = schema.TextLine(
        title=_(u"Header"),
        description=_(u"Header of the portlet."),
        required=True,
        default=u'OpenERP JavaScript Portlet')

    url = schema.URI(
        title=_(u"OpenERP URL"),
        description=_(u"Root url to your OpenERP service."),
        required=True,
        default='http://demo.vnc.biz:8085')

    dbname = schema.TextLine(
        title=_(u"Database Name"),
        description=_(u"Name of the database of your OpenERP service."),
        required=True,
        default=u'openerp_v61_demo')

    action_id = schema.Choice(
        title=_(u"Widget"),
        description=_(u"OpenERP widget to use."),
        source = 'vnccollab.theme.openerp_js.openerp_vocabulary',
        required=True,)


class Assignment(base.Assignment):
    implements(IOpenERPJSPortlet, IAttributeAnnotatable)

    header = u'OpenERP Customers'
    url = u'http://demo.vnc.biz:8085'
    dbname  = u'openerp_v61_demo'
    action_id = 22

    @property
    def title(self):
        """Return portlet header"""
        return self.header

    def __init__(self, header=header, url=url, dbname=dbname,
                 action_id=action_id):
        self.header = header
        self.url = url
        self.dbname = dbname
        self.action_id = action_id


class Renderer(base.Renderer):

    render = ZopeTwoPageTemplateFile('templates/openerp_js.pt')

    @property
    def title(self):
        """return title of feed for portlet"""
        return self.data.header

    @memoize
    def _getAuthCredentials(self):
        """Returns username and password for zimbra user."""
        mtool = getToolByName(self.context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        username, password = member.getProperty('openerp_username', ''), \
            member.getProperty('openerp_password', '')
        # password could contain non-ascii chars, ensure it's properly encoded
        return username, safe_unicode(password).encode('utf-8')

    def update(self):
        """Calculates the info needed to embed an openERP widget"""
        annotation = IAnnotations(self.data)
        login, pwd = self._getAuthCredentials()
        key = 'vnccollab.theme.openerp_js.embedded_url.{0}.{1}'.format(
                self.data.action_id, login)

        embedded_info = annotation.get(key, None)

        if embedded_info is None:
            embedded_info = self._embed(login, pwd)

            if embedded_info is not None:
                annotation[key] = embedded_info
            else:
                embedded_info = ('', '', '', '', '', 0)

        self.embedded_url, self.embedded_code, self.url, \
                self.login, self.key, _ = embedded_info
        self.action_id = self.data.action_id
        self.dbname = self.data.dbname

    def _embed(self, login, pwd):
        """Generates the OpenERP embed widget for the give user user"""
        url = self.data.url
        dbname = self.data.dbname
        model = 'share.wizard'
        action_id = self.data.action_id
        create_args = { 'name' : '{0}-{1}'.format(login, action_id),
                        'action_id' : action_id,
                        'access_mode': 'readwrite',
                        'domain' : ['|',['state','=','draft'],['state','=','open']] }
        embedded_url = ''
        embedded_code = ''

        try:
            server = xmlrpclib.ServerProxy(url + '/xmlrpc/common', allow_none=True)
            uid = server.login(dbname, login, pwd)
            server = xmlrpclib.ServerProxy(url + '/xmlrpc/object', allow_none=True)

            id = server.execute(dbname, uid, pwd, model, 'create', create_args)
            args = [id]
            server.execute(dbname, uid, pwd, model, 'go_step_1', args)
            server.execute(dbname, uid, pwd, model, 'go_step_2', args, {})
            r = server.execute(dbname, uid, pwd, model, 'export_data', args,
                               ['embed_url', 'embed_code'])
            embedded_url = r['datas'][0][0]
            embedded_code = r['datas'][0][1]
        except:
            import traceback
            traceback.print_exc()

        # Parse the embed info in embedded_url and embedded_code
        if not embedded_url:
            return None

        parsed = urlparse(embedded_url)
        query_params = parse_qs(parsed.query)
        url = '{0}://{1}'.format(parsed.scheme, parsed.netloc)
        login = query_params['login'][0]
        key = query_params['key'][0]
        action_id = re.search('(?<=,)[0-9]+', embedded_code).group(0)
        return (embedded_url, embedded_code, url, login, key, action_id)


class AddForm(base.AddForm):
    form_fields = form.Fields(IOpenERPJSPortlet)
    label = _(u"Add OpenERP JavaScript Portlet")
    description = _(u"Create an OpenERP JavaScript Portlet.")

    def create(self, data):
        return Assignment(**data)


class EditForm(base.EditForm):
    form_fields = form.Fields(IOpenERPJSPortlet)
    label = _(u"Edit OpenERP JavaScript Portlet")
    description = _(u"This portlet allows managing the OpenERP JavaScript Portlet.")



'''
How to get the action_id of a widget?

Just visit http://demo.vnc.biz:8085. Go to the page you want to embed, click the green icon in the upper left side of screen, the one with "Link or Embed..." as tooltip and follow the wizard. It will generate a url with an action_id parameter.
'''
OPENERP_VOCAB = [
        (147,  _(u'Sales - Leads')),
        (150, _(u'Sales - Opportunities')),
        (562, _(u'Sales - Contracts')),
        (60,  _(u'Sales - Customers')),
        (57,  _(u'Sales - Contacts')),
        (180, _(u'Sales - Products by Category')),
        (178, _(u'Sales - Products')),
        (158, _(u'Sales - Logged Calls')),
        (159, _(u'Sales - Scheduled Calls')),
        (196, _(u'Projects - Tasks')),
]

class OpenERPJSPortletVocabulary():
    implements(IVocabularyFactory)

    def __call__(self, context):
        items = [SimpleTerm(value, title, title) for (value, title) in OPENERP_VOCAB]
        return SimpleVocabulary(items)

openerp_vocabulary = OpenERPJSPortletVocabulary()