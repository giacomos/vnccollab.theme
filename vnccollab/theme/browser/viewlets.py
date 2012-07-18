from urllib import quote_plus
import logging
import os.path
from pyactiveresource.activeresource import ActiveResource
from pytz import timezone
from datetime import datetime

from Acquisition import aq_base, aq_inner, aq_parent
from DateTime import DateTime

from zope.interface import alsoProvides, Interface
from zope.component import getMultiAdapter, queryMultiAdapter, getUtility
from zope.i18nmessageid import MessageFactory
from zope.viewlet.interfaces import IViewlet

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import IActionCategory, IAction
from Products.CMFCore.ActionInformation import ActionInfo
from Products.CMFPlone.utils import safe_unicode, normalizeString, parent
from Products.CMFPlone.i18nl10n import monthname_msgid, weekdayname_msgid

from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.app.contentmenu.menu import FactoriesSubMenuItem
from plone.app.viewletmanager.manager import BaseOrderedViewletManager
from plone.app.layout.viewlets import common
from plone.app.layout.viewlets.interfaces import IPortalHeader
from plone.memoize.instance import memoize
from plone.registry.interfaces import IRegistry
from plone.portlets.interfaces import IPortletManager, IPortletRenderer

from Products.Carousel.config import CAROUSEL_ID
from Products.Carousel.interfaces import ICarousel
from Products.Carousel.browser.viewlet import CarouselViewlet

from cioppino.twothumbs.rate import getTally

from vnccollab.theme.portlets.zimbra_mail import logException
from vnccollab.theme import messageFactory as _
from vnccollab.theme.avatar import IAvatarUtil
from vnccollab.theme.config import FOOTER_LINKS_CAT
from vnccollab.theme.browser.interfaces import IVNCCollabHtmlHead
from vnccollab.theme.portlets import world_clock
from vnccollab.theme.settings import IWorldClockSettings
from vnccollab.theme.util import groupList, getZimbraLiveAnnotatedTasks


_pl = MessageFactory('plonelocales')
logger = logging.getLogger('vnccollab.theme.RelatedRedmineTicketsViewlet')


class TopRatedViewlet(common.ViewletBase):
    """Renders list of most rated items under given container.

    Rating system by cioppino.twothumbs.
    """

    def update(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        elems = []
        for brain in catalog(path={'depth': 20,
            'query': '/'.join(self.context.getPhysicalPath())},
            sort_on='avg_ratings',
            sort_order='reverse'):

            # skip item if nobody voted yet
            if brain.positive_ratings == 0 and brain.total_down_ratings == 0:
                continue

            elems.append({
                'title': _(safe_unicode(brain.Title)),
                'desc': _(safe_unicode(brain.Description)),
                'url': brain.getURL(),
                'type': normalizeString(brain.portal_type, encoding='utf-8'),
                'rating': {'total': brain.avg_ratings,
                           'liked': brain.positive_ratings,
                           'disliked': brain.total_down_ratings}})

        self.elems = tuple(elems)

class ActionsListViewlet(common.ViewletBase):
    """Renders internal ActionsItem List object view.

    Gets first found ActionsItem List object in first level hierarchy.
    """

    def update(self):
        self.todo = None
        for obj in self.context.objectValues():
            if getattr(obj, 'portal_type', '') == 'ActionItemList':
                self.todo = obj
                break

class LoginViewlet(common.ViewletBase):
    """Most methods are copied over from login portlet renderer"""

    def __init__(self, *args, **kw):
        super(LoginViewlet, self).__init__(*args, **kw)

        self.membership = getToolByName(self.context, 'portal_membership')
        self.context_state = getMultiAdapter((self.context, self.request),
            name=u'plone_context_state')
        self.portal_state = getMultiAdapter((self.context, self.request),
            name=u'plone_portal_state')
        self.pas_info = getMultiAdapter((self.context, self.request),
            name=u'pas_info')

    def show(self):
        if not self.portal_state.anonymous():
            return False
        if not self.pas_info.hasLoginPasswordExtractor():
            return False

        return True
        # page = self.request.get('URL', '').split('/')[-1]
        # return page not in ('login_form', '@@register')

    @property
    def available(self):
        return self.auth() is not None and self.show()

    def login_form(self):
        return '%s/login_form' % self.portal_state.portal_url()

    def mail_password_form(self):
        return '%s/mail_password_form' % self.portal_state.portal_url()

    def login_name(self):
        auth = self.auth()
        name = None
        if auth is not None:
            name = getattr(auth, 'name_cookie', None)
        if not name:
            name = '__ac_name'
        return name

    def login_password(self):
        auth = self.auth()
        passwd = None
        if auth is not None:
            passwd = getattr(auth, 'pw_cookie', None)
        if not passwd:
            passwd = '__ac_password'
        return passwd

    def join_action(self):
        context = self.context
        tool = getToolByName(context, 'portal_actions')
        join = tool.listActionInfos(action_chain='user/join', object=context)
        if len(join) > 0:
            return join[0]['url']
        return None

    def can_register(self):
        if getToolByName(self.context, 'portal_registration', None) is None:
            return False
        return self.membership.checkPermission('Add portal member',
            self.context)

    def can_request_password(self):
        return self.membership.checkPermission('Mail forgotten password',
            self.context)

    @memoize
    def auth(self, _marker=[]):
        acl_users = getToolByName(self.context, 'acl_users')
        return getattr(acl_users, 'credentials_cookie_auth', None)

class HeaderTimeViewlet(common.ViewletBase):
    """Returns current date and time in local format"""

    def update(self):
        super(HeaderTimeViewlet, self).update()

        date = DateTime()
        self.day = date.day()
        self.month = _pl(monthname_msgid(int(date.strftime('%m'))),
            default=safe_unicode(date.Month()))
        self.dayname = _pl(weekdayname_msgid(int(date.strftime('%w'))),
            default=safe_unicode(date.DayOfWeek()))
        self.datetime = self.toLocalizedTime(date, long_format=True)

    def toLocalizedTime(self, time, long_format=None, time_only = None):
        """Convert time to localized time
        """
        util = getToolByName(self.context, 'translation_service')
        return util.ulocalized_time(time, long_format, time_only, self.context,
                                    domain='plonelocales')

class PathBarViewlet(common.PathBarViewlet):
    render = ViewPageTemplateFile('templates/path_bar.pt')

class FooterViewlet(common.FooterViewlet):
    index = ViewPageTemplateFile('templates/footer.pt')

    def update(self):
        super(FooterViewlet, self).update()
        self.columns = columns = {}

        context = aq_inner(self.context)
        actions_tool = getToolByName(context, 'portal_actions')

        # check if we got root category for all column links
        if not FOOTER_LINKS_CAT in actions_tool.objectIds():
            return

        # prepare expression context for evaluating TAL expressions
        ec = actions_tool._getExprContext(context)

        # go over root category and collect all sub-categories
        container = actions_tool[FOOTER_LINKS_CAT]
        cat_ids = container.objectIds()
        for cid in ('column1', 'column2', 'column3'):
            # skip not existing categories
            if cid not in cat_ids:
                continue

            cat = container[cid]
            if not IActionCategory.providedBy(cat):
                continue

            # prepare category actions
            actions = []
            for action in cat.objectValues():
                # look only for actions
                if not IAction.providedBy(action):
                    continue

                # create actioninfo object to compile and render TAL expressions
                # and check if action is available in current circumstances
                info = ActionInfo(action, ec)
                if not (info['visible'] and info['allowed'] and
                        info['available']):
                    continue

                # and finally extract all required details from action
                desc = action.getProperty('description', None) or None
                if desc is not None:
                    desc = _(safe_unicode(desc))
                actions.append({
                    'id': info['id'],
                    'title': _(safe_unicode(info['title'])),
                    'desc': desc,
                    'url': info['url']
                })

            # finally add category to be rendered as footer column
            columns[cid] = {
                'title': _(safe_unicode(cat.getProperty('title', ''))),
                'actions': tuple(actions)
            }

        self.columns = columns

class PersonalBarViewlet(common.PersonalBarViewlet):
    index = ViewPageTemplateFile('templates/personal_bar.pt')

    def update(self):
        super(PersonalBarViewlet, self).update()

        # get personal user image
        self.user_image = None
        if not self.anonymous:
            mtool = getToolByName(self.context, 'portal_membership')
            # if no userid passes it'll return portrait of logged in user
            portrait = mtool.getPersonalPortrait()
            if portrait is not None:
                self.user_image = portrait.absolute_url()

        # render languages viewlet
        context = aq_inner(self.context)
        languages = u''
        manager = BaseOrderedViewletManager()
        alsoProvides(manager, IPortalHeader)
        viewlet = queryMultiAdapter((context, self.request, self.view,
            manager), IViewlet, name='plone.app.i18n.locales.languageselector')
        if viewlet is not None:
            viewlet = viewlet.__of__(context)
            viewlet.update()
            languages = viewlet.render()
        self.languages = languages

        # Get css style for image avatar
        self.avatar_width = 80
        self.avatar_height = 80
        self.avatar_style = ''

        if self.user_image is not None:
            img_name = os.path.basename(self.user_image)
            if img_name <> 'defaultUser.png':
                img = context.portal_memberdata.portraits[img_name]
                avatar = getUtility(IAvatarUtil)
                self.avatar_width, self.avatar_height, self.avatar_style = avatar.style(img, (80, 80))

class VNCCarouselViewlet(CarouselViewlet):
    """Customize template to fix javascript code"""

    index = ViewPageTemplateFile('templates/carousel_viewlet.pt')

class VNCCollabHeaderViewlet(common.ViewletBase):
    """Viewlet that inserts vnc header manager into plone header manager"""

    def available(self):
        """Available only if carousel is set on current folder"""
        context = aq_inner(self.context)

        manager = BaseOrderedViewletManager()
        alsoProvides(manager, IVNCCollabHtmlHead)
        viewlet = queryMultiAdapter((context, self.request, self.view, manager),
            IViewlet, name='vnccollab.theme.headercarousel')
        if viewlet is None:
            return False

        viewlet = viewlet.__of__(context)
        viewlet.update()
        return viewlet.available

class RelatedRedmineTicketsViewlet(common.ViewletBase):
    """Lists redmine tickets assigned to current object"""

    def update(self):
        self.tickets = ()
        tickets = []
        # check if settings are configured
        # check user redmine credentials and redmine url/field id
        registry = getUtility(IRegistry)
        url = registry.get('vnccollab.theme.redmine.url')
        field_id = registry.get('vnccollab.theme.redmine.plone_uid_field_id')
        username, password = self.getAuthCredentials()
        if username and password and url and field_id:
            Issue = type("Issue", (ActiveResource,), {'_site': url, '_user':
                username, '_password': password})
            # do actual calls to redmine
            try:
                # fetch opened issues belonging to authenticated user
                data = Issue.find(**{'cf_%d' % field_id: self.context.UID(),
                    'status_id': 'o', 'sort': 'updated_on:desc'})
            except Exception, e:
                logException(_(u"Error during fetching redmine tickets %s" %
                    url), context=self.context, logger=logger)
                return

            for item in data:
                info = item.to_dict()

                # skip invalid entries
                if not info.get('id') or not info.get('subject'):
                    continue

                tickets.append({
                    'id': info['id'],
                    'title': safe_unicode(info['subject']),
                    'body': safe_unicode(info.get('description', '')),
                    'url': '%s/issues/%s' % (url, info['id'])
                })

        self.tickets = tuple(tickets)

    @memoize
    def getAuthCredentials(self):
        """Returns username and password for redmine user."""
        # take username and password from authenticated user Zimbra creds
        mtool = getToolByName(self.context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        username, password = member.getProperty('redmine_username', ''), \
            member.getProperty('redmine_password', '')
        # password could contain non-ascii chars, ensure it's properly encoded
        return username, safe_unicode(password).encode('utf-8')


class RelatedZimbraTasksViewlet(common.ViewletBase):
    """Lists zimbra tasks assigned to current object"""

    def update(self):
        self.tasks = getZimbraLiveAnnotatedTasks(self.context)


class WorldClockViewlet(common.ViewletBase):
    """Shows world clock.

    It basically re-uses World Clock portlet code.
    """

    def update(self):
        context = aq_inner(self.context)
        portal = getToolByName(context, 'portal_url').getPortalObject()
        manager = getUtility(IPortletManager, name='plone.rightcolumn',
            context=portal)

        # get settings from registry
        registry = getUtility(IRegistry)
        try:
            settings = registry.forInterface(IWorldClockSettings)
        except KeyError, e:
            # in case settings are not there yet
            self.world_clock = ''
            return

        tz_1 = settings.tz_1
        skin_1 = settings.skin_1
        radius_1 = settings.radius_1
        no_seconds_1 = settings.no_seconds_1
        tz_2 = settings.tz_2
        skin_2 = settings.skin_2
        radius_2 = settings.radius_2
        no_seconds_2 = settings.no_seconds_2
        tz_3 = settings.tz_3
        skin_3 = settings.skin_3
        radius_3 = settings.radius_3
        no_seconds_3 = settings.no_seconds_3

        assignment = world_clock.Assignment(header=u'', tz_1=tz_1,
            skin_1=skin_1, radius_1=radius_1, no_seconds_1=no_seconds_1,
            tz_2=tz_2, skin_2=skin_2, radius_2=radius_2,
            no_seconds_2=no_seconds_2, tz_3=tz_3, skin_3=skin_3,
            radius_3=radius_3, no_seconds_3=no_seconds_3)
        renderer = queryMultiAdapter((context, self.request, self.view, manager,
            assignment), IPortletRenderer)
        renderer.update()
        self.world_clock = renderer.render()

class IExternalEditable(Interface):
    """Marker Interface for objects than can be edited by zopeedit."""

class ZopeEditViewlet(common.ViewletBase):
    """Link for external editor"""
    def external_editor_url(self):
        path = self.context.absolute_url_path()
        parent = os.path.dirname(path)
        me = os.path.basename(path)
        return os.path.join(parent, 'externalEdit_', me)

class AddContentAreaViewlet(common.ViewletBase):
    """Add new content form"""

    def getAddLinks(self):
        """Returns tuple containing list of links for 1st, 2nd and file zone
        areas.
        """
        context = aq_inner(self.context)
        submenu = FactoriesSubMenuItem(context, self.request)
        folder = self.getFolder()
        folder_url = folder.absolute_url()
        idnormalizer = getUtility(IIDNormalizer)
        result = []
        add_file = ''
        for atype in submenu._addableTypesInContext(folder):
            id = atype.getId()
            if id == 'File':
                add_file = '%s/upload-file' % folder_url
            result.append({
                'id': id,
                'title': atype.Title(),
                'desc': atype.Description(),
                'url': '%s/createObject?type_name=%s' % (folder_url,
                    quote_plus(id)),
                'icon': '%s/add_content_area/metabox_icon_%s.png' % (
                    self.site_url, idnormalizer.normalize(id))
            })

        if len(result) == 0:
            return {}

        # group result by columns
        result = groupList(result, groups_number=2)
        data = {'column1': result[0],
                'column2': (),
                'column3': add_file}
        if len(result) > 1:
            data['column2'] = result[1]

        return data

    def getFolderTitle(self, folder):
        # add parent title
        ptitle = ''
        parent = aq_parent(aq_inner(folder))
        if parent:
            ptitle = getattr(parent, 'Title', lambda:'')()
            if ptitle:
                ptitle = ' (%s)' % ptitle
        return '%s%s' % (getattr(folder, 'Title', lambda:'')(), ptitle)

    @memoize
    def getFolder(self):
        context = aq_inner(self.context)
        submenu = FactoriesSubMenuItem(context, self.request)
        if submenu.context_state.is_default_page():
            return parent(context)
        return submenu._addContext()
