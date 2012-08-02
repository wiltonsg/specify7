import os
from xml.etree import ElementTree

from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import views as auth_views
from django.conf import settings

from specify.models import Collection, Spappresourcedata, Spappresourcedir, Specifyuser

DIR_LEVELS = ['Personal', 'UserType', 'Collection', 'Discipline', 'Common', 'Backstop']

disc_file = os.path.join(settings.SPECIFY_CONFIG_DIR, "disciplines.xml")

disciplines = ElementTree.parse(disc_file)

discipline_dirs = dict( (disc.attrib['name'], disc.attrib.get('folder', disc.attrib['name'])) \
                            for disc in disciplines.findall('discipline') )

def with_collection(func):
    @login_required
    def wrapped(request, *args, **kwargs):
        try:
            collection = Collection.objects.get(id=int(request.session.get('collection', '')))
        except ValueError:
            return HttpResponseBadRequest('bad collection id', content_type="text/plain")
        except Collection.DoesNotExist:
            return HttpResponseBadRequest('collection does not exist', content_type="text/plain")
        return func(request, collection, *args, **kwargs)
    return wrapped

def login(request):
    if request.method == 'POST':
        request.session['collection'] = request.POST['collection_id']

    kwargs = {
        'template_name': 'login.html',
        'extra_context': { 'collections': Collection.objects.all() } }
    return auth_views.login(request, **kwargs)

def logout(request):
    return auth_views.logout(request, template_name='logged_out.html')

@login_required
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def collection(request):
    if request.method == 'POST':
        try:
            collection = Collection.objects.get(id=int(request.raw_post_data))
        except ValueError:
            return HttpResponseBadRequest('bad collection id', content_type="text/plain")
        except Collection.DoesNotExist:
            return HttpResponseBadRequest('collection does not exist', content_type="text/plain")
        request.session['collection'] = str(collection.id)
        return HttpResponse('ok')
    else:
        collection = request.session.get('collection', '')
        return HttpResponse(collection, content_type="text/plain")

@require_GET
@with_collection
def viewsets(request, collection, level):
    user = Specifyuser.objects.get(name=request.user.username)
    discipline = collection.discipline
    discipline_dir = discipline_dirs[discipline.type]
    usertype = user.usertype.replace(' ', '').lower()

    viewset_filters = {
        'Columns'    : ('ispersonal', 'usertype', 'collection', 'discipline'),
        'Personal'   : (True        , usertype  , collection  , discipline)  ,
        'UserType'   : (False       , usertype  , collection  , discipline)  ,
        'Collection' : (False       , None      , collection  , discipline)  ,
        'Discipline' : (False       , None      , None        , discipline)  ,
        'Common'     : (False       , "Common"  , None        , None)}

    def get_viewset(level):
        columns, values = viewset_filters['Columns'], viewset_filters[level]
        filters = dict(zip(columns, values))
        if filters['ispersonal']: filters['specifyuser'] = user
        dirs = Spappresourcedir.objects.filter(**filters)
        objs = Spappresourcedata.objects.filter(spviewsetobj__spappresourcedir__in=dirs)
        return [ElementTree.XML(o.data) for o in objs]

    viewset_paths = {
        'UserType'  : (discipline_dir, usertype),
        'Discipline': (discipline_dir,)         ,
        'Common'    : ('common'      ,)         ,
        'Backstop'  : ('backstop'    ,)}

    def load_viewset(level):
        path = viewset_paths.get(level, None)
        if not path: return []
        path = os.path.join(settings.SPECIFY_CONFIG_DIR, *path)
        registry = ElementTree.parse(os.path.join(path, 'viewset_registry.xml'))
        return [ElementTree.parse(os.path.join(path, f.attrib['file'])).getroot() \
                    for f in registry.findall('file')]

    try:
        dir_level = DIR_LEVELS[int(level)]
    except IndexError:
        raise Http404()

    if dir_level == 'Backstop': viewsets = load_viewset('Backstop')
    else: viewsets = get_viewset(dir_level) or load_viewset(dir_level)

    result = ElementTree.Element('viewsets')
    for viewset in viewsets: result.append(viewset)
    return HttpResponse(ElementTree.tostring(result), content_type="text/xml")

@require_GET
@with_collection
def schema_localization(request, collection):
    def read_schema_localization(path):
        with open(path) as schema_localization:
            xml = schema_localization.read()
        return xml

    discipline_dir = discipline_dirs[collection.discipline.type]
    path = os.path.join(settings.SPECIFY_CONFIG_DIR, discipline_dir, 'schema_localization.xml')
    try:
        xml = read_schema_localization(path)
    except IOError:
        path = os.path.join(settings.SPECIFY_CONFIG_DIR, 'schema_localization.xml')
        xml = read_schema_localization(path)

    return HttpResponse(xml, content_type='text/xml')