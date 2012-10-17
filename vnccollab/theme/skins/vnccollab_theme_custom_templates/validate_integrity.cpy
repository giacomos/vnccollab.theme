## Script (Python) "validate_integrity"
##title=Validate Integrity
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=
##

from Products.Archetypes import PloneMessageFactory as _
from Products.Archetypes.utils import addStatusMessage

request = context.REQUEST
errors = {}
errors = context.validate(REQUEST=request, errors=errors, data=1, metadata=0)

if errors:
    message = _(u'Please correct the indicated errors.')
    addStatusMessage(request, message, type='error')
    return state.set(status='failure', errors=errors)
else:
    # vipod: do not redirect to view action in case we already have redirect header in request
    if request.RESPONSE.getHeader('Location'):
        return state.set(status='redirect')
    else:
        message = _(u'Changes saved.')
        addStatusMessage(request, message)
        return state.set(status='success')
