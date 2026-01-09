from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from .models import *
from .serializers import *

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['category', 'in_stock', 'is_featured', 'is_trending']
    ordering_fields = ['price', 'name', 'id', 'created_at', 'views_count', 'likes_count']
    ordering = ['id']
    search_fields = ['name', 'category', 'description']
    
    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        product.views_count += 1
        product.save()
        
        if request.user.is_authenticated:
            RecentlyViewed.objects.update_or_create(
                user=request.user,
                product=product
            )
        
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured = self.queryset.filter(is_featured=True)
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        trending = self.queryset.filter(is_trending=True).order_by('-views_count')[:10]
        serializer = self.get_serializer(trending, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        if not request.user.is_authenticated:
            products = self.queryset.order_by('-views_count', '-likes_count')[:6]
        else:
            # AI-based recommendations
            recent_views = RecentlyViewed.objects.filter(user=request.user)[:5]
            categories = [rv.product.category for rv in recent_views]
            
            # Get user's liked products
            liked_products = ProductLike.objects.filter(user=request.user).values_list('product__category', flat=True)
            categories.extend(liked_products)
            
            # Recommend from same categories
            products = self.queryset.filter(category__in=categories).exclude(
                id__in=[rv.product.id for rv in recent_views]
            ).order_by('-average_rating', '-views_count')[:6]
            
            if len(products) < 6:
                extra = self.queryset.order_by('-views_count')[:6-len(products)]
                products = list(products) + list(extra)
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)
    
    def create(self, request):
        cart_items = CartItem.objects.filter(user=request.user)
        
        if not cart_items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        total = sum(item.get_total_price() for item in cart_items)
        discount = 0
        coupon = None
        
        coupon_id = request.data.get('coupon_id')
        if coupon_id:
            try:
                coupon = Coupon.objects.get(id=coupon_id)
                if coupon.is_valid():
                    discount = coupon.calculate_discount(total)
                    coupon.used_count += 1
                    coupon.save()
            except Coupon.DoesNotExist:
                pass
        
        final_amount = total - discount
        
        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            discount_amount=discount,
            final_amount=final_amount,
            coupon=coupon,
            payment_method=request.data.get('payment_method', 'COD'),
            shipping_address=request.data.get('shipping_address', ''),
            tracking_number=self.generate_tracking_number(),
            estimated_delivery=timezone.now().date() + timedelta(days=7)
        )
        
        for cart_item in cart_items:
            variant_info = ""
            if cart_item.variant:
                variant_info = f"{cart_item.variant.size} {cart_item.variant.color}"
            
            OrderItem.objects.create(
                order=order,
                product_name=cart_item.product.name,
                product_price=cart_item.product.price + (cart_item.variant.price_adjustment if cart_item.variant else 0),
                quantity=cart_item.quantity,
                variant_info=variant_info
            )
            
            cart_item.product.stock_quantity -= cart_item.quantity
            cart_item.product.save()
        
        cart_items.delete()
        
        # Send Email Notification
        # Send Email Notification (non-blocking)
try:
    self.send_order_email(request.user, order)
except Exception as e:
    print(f"Email failed: {e}")
    # Continue without failing the order

        
        # Create notification
        Notification.objects.create(
            user=request.user,
            title="Order Placed Successfully! 🎉",
            message=f"Your order #{order.id} has been placed. Total: ₹{final_amount}. Tracking: {order.tracking_number}",
            notification_type="order"
        )
        
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def generate_tracking_number(self):
        import random
        import string
        return 'TRK' + ''.join(random.choices(string.digits, k=10))
    
    def send_order_email(self, user, order):
    subject = f'Order Confirmation #{order.id} - ShopHub'
    message = f'''Hi {user.username},

Thank you for your order!

Order Details:
- Order ID: #{order.id}
- Total Amount: ₹{order.final_amount}
- Discount: ₹{order.discount_amount}
- Payment Method: {order.payment_method}
- Tracking Number: {order.tracking_number}
- Estimated Delivery: {order.estimated_delivery}

Items:
'''
    
    for item in order.items.all():
        message += f'\n- {item.product_name} x {item.quantity} = ₹{item.product_price * item.quantity}'
    
    message += f'''

Shipping Address:
{order.shipping_address}

Track your order at: https://ecommerce-frontend-kappa-henna.vercel.app

Thank you for shopping with us!

ShopHub Team
'''
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email] if user.email else [],
        fail_silently=True,
    )
    except Exception as e:
        print(f"Failed to send email: {e}")

        
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            
            # Send status update email
            subject = f'Order Status Update #{order.id} - ShopHub'
            message = f'''
            Hi {order.user.username},

            Your order #{order.id} status has been updated to: {new_status}

            Tracking Number: {order.tracking_number}
            Estimated Delivery: {order.estimated_delivery}

            Thank you for your patience!

            ShopHub Team
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [order.user.email] if order.user.email else [],
                fail_silently=True,
            )
            
            Notification.objects.create(
                user=order.user,
                title=f"Order {new_status} 📦",
                message=f"Your order #{order.id} is now: {new_status}",
                notification_type="order_status"
            )
            
            return Response(self.get_serializer(order).data)
        
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)
    
    def create(self, request):
        product_id = request.data.get('product_id')
        variant_id = request.data.get('variant_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id)
            except ProductVariant.DoesNotExist:
                return Response({'error': 'Variant not found'}, status=status.HTTP_404_NOT_FOUND)
        
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = self.get_serializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'])
    def update_quantity(self, request, pk=None):
        cart_item = self.get_object()
        quantity = request.data.get('quantity')
        
        if quantity and quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data)
        else:
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        self.get_queryset().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WishlistItem.objects.filter(user=self.request.user)
    
    def create(self, request):
        product_id = request.data.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        wishlist_item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            return Response({'message': 'Already in wishlist'}, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(wishlist_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def remove_by_product(self, request):
        product_id = request.data.get('product_id')
        try:
            wishlist_item = WishlistItem.objects.get(user=request.user, product_id=product_id)
            wishlist_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except WishlistItem.DoesNotExist:
            return Response({'error': 'Not in wishlist'}, status=status.HTTP_404_NOT_FOUND)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        product_id = self.request.query_params.get('product_id')
        if product_id:
            return Review.objects.filter(product_id=product_id)
        return Review.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ReviewCreateUpdateSerializer
        return ReviewSerializer
    
    def create(self, request):
        product_id = request.data.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        existing_review = Review.objects.filter(user=request.user, product=product).first()
        if existing_review:
            return Response({'error': 'You already reviewed this product'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, product=product)
            return Response(ReviewSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductLikeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        product_id = request.data.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        like, created = ProductLike.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if created:
            product.likes_count += 1
            product.save()
            return Response({'liked': True, 'likes_count': product.likes_count})
        else:
            like.delete()
            product.likes_count = max(0, product.likes_count - 1)
            product.save()
            return Response({'liked': False, 'likes_count': product.likes_count})


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Coupon.objects.filter(is_active=True)
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        code = request.data.get('code')
        amount = request.data.get('amount', 0)
        
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return Response({'valid': False, 'error': 'Invalid coupon'}, status=status.HTTP_404_NOT_FOUND)
        
        if not coupon.is_valid():
            return Response({'valid': False, 'error': 'Coupon expired or limit reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        if amount < coupon.min_purchase_amount:
            return Response({
                'valid': False,
                'error': f'Minimum purchase: ₹{coupon.min_purchase_amount}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        discount = coupon.calculate_discount(amount)
        
        return Response({
            'valid': True,
            'coupon_id': coupon.id,
            'discount': discount,
            'final_amount': amount - discount
        })


class RecentlyViewedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RecentlyViewedSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RecentlyViewed.objects.filter(user=self.request.user)[:10]


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all marked as read'})


class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        else:
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# NEW: Payment Gateway Endpoint
class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """Create Razorpay order"""
        amount = request.data.get('amount')  # Amount in rupees
        
        # For demo purposes - you'd integrate with actual Razorpay here
        order_data = {
            'order_id': f'order_{timezone.now().timestamp()}',
            'amount': amount * 100,  # Razorpay uses paise
            'currency': 'INR',
            'status': 'created'
        }
        
        return Response(order_data)
    
    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        """Verify Razorpay payment"""
        # In production, verify signature here
        payment_id = request.data.get('payment_id')
        order_id = request.data.get('order_id')
        
        return Response({
            'success': True,
            'message': 'Payment verified successfully'
        })
