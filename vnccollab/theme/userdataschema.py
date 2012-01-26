from zope import schema
from zope.interface import implements

from plone.app.users import userdataschema as base

from vnccollab.theme import messageFactory as _


class UserDataSchemaProvider(object):
    implements(base.IUserDataSchemaProvider)

    def getSchema(self):
        """
        """
        return IUserDataSchema

class IUserDataSchema(base.IUserDataSchema):

    zimbra_username = schema.ASCIILine(
        title=_("Zimbra Username"),
        description=_(u"We need this field in order to display your Zimbra "
                      "related information, like mail box, calendar, contacts, "
                      "etc..."),
        required=False)

    zimbra_password = schema.Password(
        title=_("Zimbra Password"),
        description=_(u"We need this field in order to display your Zimbra "
                      "related information, like mail box, calendar, contacts, "
                      "etc..."),
        required=False)
    
    etherpad_url = schema.URI(
        title=_(u"Etherpad URL"),
        description=_(u"Root url to your Etherpad service. This field is "
            "usually useful in case every user got his own Etherpad url instead"
            " of using one global domain for all users."),
        required=False)
    
    etherpad_username = schema.ASCIILine(
        title=_("Etherpad Username"),
        description=_(u"We need this field in order to display your Etherpad "
                      "related information, like single pad or whole list of "
                      "pads, etc..."),
        required=False)

    etherpad_password = schema.Password(
        title=_("Etherpad Password"),
        description=_(u"We need this field in order to display your Etherpad "
                      "related information, like single pad or whole list of "
                      "pads, etc..."),
        required=False)
    
    openerp_username = schema.ASCIILine(
        title=_("OpenERP Username"),
        description=_(u"We need this field in order to display your OpenERP "
                      "related information."),
        required=False)

    openerp_password = schema.Password(
        title=_("OpenERP Password"),
        description=_(u"We need this field in order to display your OpenERP "
                      "related information."),
        required=False)
