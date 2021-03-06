#
# This file is part of Fidus Writer <http://www.fiduswriter.org>
#
# Copyright (C) 2013 Takuto Kojima, Johannes Wilm
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpRequest
from django.utils import simplejson, timezone
from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.template import RequestContext
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.conf import settings
from django.core.mail import send_mail

from text.models import Text, AccessRight
from avatar.util import get_primary_avatar, get_default_avatar_url

from avatar.templatetags.avatar_tags import avatar_url

from django.core.serializers.python import Serializer

from django.db.models import Q
import dateutil.parser


from django.core.serializers.python import Serializer

class SimpleSerializer(Serializer):
    def end_object( self, obj ):
        self._current['id'] = obj._get_pk_val()
        self.objects.append( self._current )
serializer = SimpleSerializer()

def get_accessrights(ars):
    ret = []
    for ar in ars :
        the_avatar = get_primary_avatar(ar.user, 80)
        if the_avatar :
            the_avatar = the_avatar.avatar_url(80)
        else:
            the_avatar = get_default_avatar_url()
        ret.append({
            'text_id': ar.text.id,
            'user_id': ar.user.id,
            'user_name': ar.user.readable_name,
            'rights': ar.rights,
            'avatar': the_avatar
        })
    return ret

@login_required
def index(request):
    response = {}
    response.update(csrf(request))
    return render_to_response('text/index.html',
        response,
        context_instance=RequestContext(request))

@login_required
def get_documentlist_extra_js(request):
    response={}
    status = 405
    if request.is_ajax() and request.method == 'POST':
        status = 200
        ids = request.POST['ids'].split(',')
        #documents = Text.objects.filter(Q(owner=request.user) | Q(accessright__user=request.user)).filter(id__in=ids)
        documents = Text.objects.filter(id__in=ids)
        response['documents'] = serializer.serialize(documents, fields=('contents','id','comments','settings','metadata'))
    return HttpResponse(
        simplejson.dumps(response),
        content_type = 'application/json; charset=utf8',
        status=status
    )   

def documents_list(request):
    documents = Text.objects.filter(Q(owner=request.user) | Q(accessright__user=request.user)).order_by('-updated')
    output_list=[]
    for document in documents :
        access_right = 'w' if document.owner == request.user else AccessRight.objects.get(user=request.user,text=document).rights
        date_format = '%d/%m/%Y'
        date_obj = dateutil.parser.parse(str(document.added))
        added = date_obj.strftime(date_format)
        date_obj = dateutil.parser.parse(str(document.updated))
        updated = date_obj.strftime(date_format)
        is_owner = False
        if document.owner == request.user:
            is_owner = True
        output_list.append({
            'id': document.id,
            'title': document.title,
            'is_owner': is_owner,
            'owner': document.owner.id,
            'owner_name': document.owner.readable_name,
            'owner_avatar': avatar_url(document.owner,80),
            'added': added,
            'updated': updated,
            #'is_locked': document.is_locked(),
            'rights': access_right
        })
    return output_list
    
@login_required
def get_documentlist_js(request):
    response={}
    status = 405
    if request.is_ajax() and request.method == 'POST':
        status = 200
        response['documents'] = documents_list(request)
        response['team_members']=[]
        for team_member in request.user.leader.all():
            tm_object = {}
            tm_object['id'] = team_member.member.id
            tm_object['name'] = team_member.member.readable_name
            tm_object['avatar'] = avatar_url(team_member.member,80)
            response['team_members'].append(tm_object)
        response['user']={}
        response['user']['id']=request.user.id
        response['user']['name']=request.user.readable_name
        response['user']['avatar']=avatar_url(request.user,80)            
        response['access_rights'] = get_accessrights(AccessRight.objects.filter(text__owner=request.user))
    return HttpResponse(
        simplejson.dumps(response),
        content_type = 'application/json; charset=utf8',
        status=status
    )        


@login_required
def editor(request):
    response = {}
    
    return render_to_response('text/editor.html', 
        response,
        context_instance=RequestContext(request))
    
@login_required    
def delete_js(request):
    response = {}
    status = 405
    if request.is_ajax() and request.method == 'POST':
        doc_id = int(request.POST['id'])
        document = Text.objects.get(pk=doc_id,owner=request.user)
        document.delete()
        status = 200
    return HttpResponse(
        simplejson.dumps(response),
        content_type = 'application/json; charset=utf8',
        status=status
    )            

def send_share_notification(request, doc_id, collaborator_id, tgt_right):
    owner = request.user.readable_name
    document = Text.objects.get(id=doc_id)
    collaborator = User.objects.get(id=collaborator_id)
    collaborator_name = collaborator.readable_name
    collaborator_email = collaborator.email
    document_title = document.title
    if len(document_title)==0:
        document_title = _('Untitled')
    right = 'read'
    if tgt_right == 'w':
        right = 'read and write'
    link = HttpRequest.build_absolute_uri(request, document.get_absolute_url())
    message_body = _('Hey %(collaborator_name)s,\n%(owner)s has shared the document \'%(document)s\' with you and given you %(right)s access rights. \nAccess the document through this link: %(link)s') % {'owner': owner, 'right': right, 'collaborator_name': collaborator_name, 'link': link, 'document': document_title}
    send_mail(_('Document shared:')+' '+document_title, message_body, settings.DEFAULT_FROM_EMAIL,
        [collaborator_email], fail_silently=True)

def send_share_upgrade_notification(request, doc_id, collaborator_id):
    owner = request.user.readable_name
    document = Text.objects.get(id=doc_id)
    collaborator = User.objects.get(id=collaborator_id)
    collaborator_name = collaborator.readable_name
    collaborator_email = collaborator.email
    link = HttpRequest.build_absolute_uri(request, document.get_absolute_url())
    message_body = _('Hey %(collaborator_name)s,\n%(owner)s has given you write access rights to a Fidus Writer document.\nAccess the document through this link: %(link)s') % {'owner': owner, 'collaborator_name': collaborator_name, 'link': link}
    send_mail(_('Fidus Writer document write access'), message_body, settings.DEFAULT_FROM_EMAIL,
        [collaborator_email], fail_silently=True)


@login_required
@transaction.commit_on_success
def access_right_save_js(request):
    status = 405
    response={}
    if request.is_ajax() and request.method == 'POST':
        tgt_documents = request.POST.getlist('documents[]')
        tgt_users = request.POST.getlist('collaborators[]')
        tgt_rights = request.POST.getlist('rights[]')
        for tgt_doc in tgt_documents:
            doc_id = int(tgt_doc)
            try:
                the_doc = Text.objects.get(pk=doc_id, owner=request.user)
            except ObjectDoesNotExist:
                continue
            x = 0
            for tgt_user in tgt_users :
                collaborator_id = int(tgt_user)
                try:
                    tgt_right = tgt_rights[x]
                except IndexError:
                    tgt_right = 'r'
                if tgt_right == 'd':
                    # Status 'd' means the access right is marked for deletion.
                    try:
                        access_right = AccessRight.objects.get(text_id = doc_id, user_id = collaborator_id)
                        access_right.delete()
                    except:
                        pass
                else:
                    try:
                        access_right = AccessRight.objects.get(text_id = doc_id, user_id = collaborator_id)
                        if access_right.rights != tgt_right:
                            access_right.rights = tgt_right
                            if tgt_right == 'w':
                                send_share_upgrade_notification(request, doc_id, collaborator_id)                            
                    except ObjectDoesNotExist:
                        access_right = AccessRight.objects.create(
                            text_id = doc_id,
                            user_id = collaborator_id,
                            rights= tgt_right,
                        )
                        send_share_notification(request, doc_id, collaborator_id, tgt_right)
                    access_right.save()
                x += 1
        response['access_rights'] = get_accessrights(AccessRight.objects.filter(text__owner=request.user))
        status = 201
    return HttpResponse(
        simplejson.dumps(response),
        content_type = 'application/json; charset=utf8',
        status=status
    )