from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Ticket, Category, Priority, Status, Comment, TicketHistory, Attachment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at']


class PrioritySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = Priority
        fields = ['id', 'name', 'display_name', 'level', 'color']


class StatusSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = Status
        fields = ['id', 'name', 'display_name', 'is_closed']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'ticket', 'user', 'content', 'is_internal', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class TicketHistorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = TicketHistory
        fields = ['id', 'ticket', 'user', 'field_name', 'old_value', 'new_value', 'created_at']


class AttachmentSerializer(serializers.ModelSerializer):
    """serializer para archivos adjuntos"""
    uploaded_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    file_extension = serializers.CharField(source='get_file_extension', read_only=True)
    is_image = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'ticket', 'uploaded_by', 'file', 'file_url', 
            'filename', 'file_size', 'file_size_display', 'file_type', 
            'file_extension', 'is_image', 'uploaded_at', 'description'
        ]
        read_only_fields = ['uploaded_by', 'filename', 'file_size', 'file_type', 'uploaded_at']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class TicketListSerializer(serializers.ModelSerializer):
    """serializer simplificado para listas"""
    category = CategorySerializer(read_only=True)
    priority = PrioritySerializer(read_only=True)
    status = StatusSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_number', 'title', 'category', 'priority', 
            'status', 'created_by', 'assigned_to', 'created_at', 
            'updated_at', 'comments_count'
        ]


class TicketDetailSerializer(serializers.ModelSerializer):
    """serializer completo para detalles"""
    category = CategorySerializer(read_only=True)
    priority = PrioritySerializer(read_only=True)
    status = StatusSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    history = TicketHistorySerializer(many=True, read_only=True)
    attachments_files = AttachmentSerializer(many=True, read_only=True)
    
    #IDs para escritura
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), 
        source='category', 
        write_only=True
    )
    priority_id = serializers.PrimaryKeyRelatedField(
        queryset=Priority.objects.all(), 
        source='priority', 
        write_only=True
    )
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), 
        source='status', 
        write_only=True
    )
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), 
        source='assigned_to', 
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_number', 'title', 'description', 
            'category', 'category_id', 'priority', 'priority_id', 
            'status', 'status_id', 'created_by', 'assigned_to', 
            'assigned_to_id', 'created_at', 'updated_at', 
            'resolved_at', 'closed_at', 'attachments', 'tags',
            'comments', 'history', 'attachments_files'
        ]
        read_only_fields = [
            'ticket_number', 'created_by', 'created_at', 
            'updated_at', 'resolved_at', 'closed_at'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TicketCreateSerializer(serializers.ModelSerializer):
    """serializer simplificado para creacion"""
    
    class Meta:
        model = Ticket
        fields = [
            'title', 'description', 'category', 'priority', 
            'status', 'assigned_to', 'tags'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)