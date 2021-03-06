# -*- coding: utf-8 -*-
from openregistry.lots.core.utils import (
    get_file,
    update_file_content_type,
    json_view,
    context_unpack,
    APIResource,
    save_lot,
    oplotsresource,
    apply_patch,
)

from openregistry.lots.core.validation import (
    validate_file_upload,
    validate_document_data,
    validate_patch_document_data,
)
from openregistry.lots.core.validation import (
    validate_lot_document_update_not_by_author_or_lot_owner
)
from openregistry.lots.loki.validation import (
    validate_document_operation_in_not_allowed_lot_status,
    rectificationPeriod_document_validation
)

post_validators = (
    validate_file_upload,
    validate_document_operation_in_not_allowed_lot_status,
    rectificationPeriod_document_validation
)
put_validators = (
    validate_document_data,
    validate_document_operation_in_not_allowed_lot_status,
    validate_lot_document_update_not_by_author_or_lot_owner,
    rectificationPeriod_document_validation
)
patch_validators = (
    validate_patch_document_data,
    validate_document_operation_in_not_allowed_lot_status,
    validate_lot_document_update_not_by_author_or_lot_owner,
    rectificationPeriod_document_validation
)



@oplotsresource(name='loki:Lot Documents',
                collection_path='/lots/{lot_id}/documents',
                path='/lots/{lot_id}/documents/{document_id}',
                lotType='loki',
                description="Lot related binary files (PDFs, etc.)")
class LotDocumentResource(APIResource):

    @json_view(permission='view_lot')
    def collection_get(self):
        """Lot Documents List"""
        if self.request.params.get('all', ''):
            collection_data = [i.serialize("view") for i in self.context.documents]
        else:
            collection_data = sorted(dict([
                (i.id, i.serialize("view"))
                for i in self.context.documents
            ]).values(), key=lambda i: i['dateModified'])
        return {'data': collection_data}

    @json_view(content_type="application/json", permission='upload_lot_documents', validators=post_validators)
    def collection_post(self):
        """Lot Document Upload"""
        document = self.request.validated['document']
        document.author = self.request.authenticated_role
        self.context.documents.append(document)
        if save_lot(self.request):
            self.LOGGER.info('Created lot document {}'.format(document.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'lot_document_create'}, {'document_id': document.id}))
            self.request.response.status = 201
            document_route = self.request.matched_route.name.replace("collection_", "")
            self.request.response.headers['Location'] = self.request.current_route_url(_route_name=document_route, document_id=document.id, _query={})
            return {'data': document.serialize("view")}

    @json_view(permission='view_lot')
    def get(self):
        """Lot Document Read"""
        if self.request.params.get('download'):
            return get_file(self.request)
        document = self.request.validated['document']
        document_data = document.serialize("view")
        document_data['previousVersions'] = [
            i.serialize("view")
            for i in self.request.validated['documents']
            if i.url != document.url
        ]
        return {'data': document_data}

    @json_view(content_type="application/json", permission='upload_lot_documents', validators=put_validators)
    def put(self):
        """Lot Document Update"""
        document = self.request.validated['document']
        self.request.validated['lot'].documents.append(document)
        if save_lot(self.request):
            self.LOGGER.info('Updated lot document {}'.format(self.request.context.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'lot_document_put'}))
            return {'data': document.serialize("view")}

    @json_view(content_type="application/json", permission='upload_lot_documents', validators=patch_validators)
    def patch(self):
        """Lot Document Update"""
        if apply_patch(self.request, src=self.request.context.serialize()):
            update_file_content_type(self.request)
            self.LOGGER.info('Updated lot document {}'.format(self.request.context.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'lot_document_patch'}))
            return {'data': self.request.context.serialize("view")}
