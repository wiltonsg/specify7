import logging
import json

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache

from ..specify.models import Collection
from ..specify.api import toJson, uri_for_model
from ..specify.views import login_maybe_required, apply_access_control

from . import models
from .queryfield import QueryField
from .execution import execute, run_ephemeral_query, do_export, recordset

logger = logging.getLogger(__name__)

def value_from_request(field, get):
    try:
        return get['f%s' % field.spQueryFieldId]
    except KeyError:
        return None

@require_GET
@login_maybe_required
@never_cache
def query(request, id):
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))

    with models.session_context() as session:
        sp_query = session.query(models.SpQuery).get(int(id))
        distinct = sp_query.selectDistinct
        tableid = sp_query.contextTableId
        count_only = sp_query.countOnly

        field_specs = [QueryField.from_spqueryfield(field, value_from_request(field, request.GET))
                       for field in sorted(sp_query.fields, key=lambda field: field.position)]

        data = execute(session, request.specify_collection, request.specify_user,
                       tableid, distinct, count_only, field_specs, limit, offset)

    return HttpResponse(toJson(data), content_type='application/json')


@require_POST
@csrf_exempt
@login_maybe_required
@never_cache
def ephemeral(request):
    try:
        spquery = json.load(request)
    except ValueError as e:
        return HttpResponseBadRequest(e)
    data = run_ephemeral_query(request.specify_collection, request.specify_user, spquery)
    return HttpResponse(toJson(data), content_type='application/json')


@require_POST
@csrf_exempt
@login_maybe_required
@never_cache
def export(request):
    try:
        spquery = json.load(request)
    except ValueError as e:
        return HttpResponseBadRequest(e)

    logger.info('export query: %s', spquery)

    if 'collectionid' in spquery:
        collection = Collection.objects.get(pk=spquery['collectionid'])
        logger.debug('forcing collection to %s', collection.collectionname)
    else:
        collection = request.specify_collection

    do_export.delay(spquery, collection, request.specify_user)
    return HttpResponse('OK', content_type='text/plain')


@require_POST
@csrf_exempt
@login_maybe_required
@apply_access_control
@never_cache
def make_recordset(request):
    try:
        recordset_info = json.load(request)
    except ValueError as e:
        return HttpResponseBadRequest(e)

    new_rs_id = recordset(request.specify_collection, request.specify_user,
                          request.specify_user_agent, recordset_info)

    return HttpResponseRedirect(uri_for_model('recordset', new_rs_id))

