from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'size', 'color', 'stock_quantity', 'price_adjustment']


class ProductSerializer(serializers.ModelSerializer):
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    variants = ProductVariantSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'original_price', 'category', 
            'in_stock', 'stock_quantity', 'image', 'image_2', 'image_3',
            'is_featured', 'is_trending', 'likes_count', 'views_count',
            'average_rating', 'review_count', 'discount_percentage', 'variants', 'created_at'
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    variant = ProductVariantSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    variant_id = serializers.IntegerField(write_only=True, required=False)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'variant', 'variant_id', 'quantity', 'added_at', 'total_price']
    
    def get_total_price(self, obj):
        return obj.get_total_price()


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_price', 'quantity', 'variant_info']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'username', 'total_amount', 'discount_amount', 'final_amount',
            'coupon', 'created_at', 'updated_at', 'status', 'payment_status', 'payment_method',
            'tracking_number', 'estimated_delivery', 'shipping_address', 'items'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = WishlistItem
        fields = ['id', 'product', 'product_id', 'added_at']


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'product', 'user', 'username', 'rating', 'comment', 'helpful_count', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at', 'helpful_count']


class ReviewCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['rating', 'comment']


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'discount_type', 'discount_value', 'min_purchase_amount', 
                  'max_discount_amount', 'valid_from', 'valid_until', 'is_active']


class ProductLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductLike
        fields = ['id', 'product', 'user', 'created_at']


class RecentlyViewedSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = RecentlyViewed
        fields = ['id', 'product', 'viewed_at']


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email', 'phone', 'address', 'city', 'state', 'pincode', 'avatar']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
