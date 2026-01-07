from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
import random
import string

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.IntegerField()
    original_price = models.IntegerField(null=True, blank=True)  # For discounts
    category = models.CharField(max_length=100)
    in_stock = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=100)
    image = models.URLField(blank=True)
    image_2 = models.URLField(blank=True)
    image_3 = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    likes_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def average_rating(self):
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0
    
    def review_count(self):
        return self.reviews.count()
    
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100)
        return 0


class ProductVariant(models.Model):
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, blank=True)
    color = models.CharField(max_length=50, blank=True)
    stock_quantity = models.IntegerField(default=0)
    price_adjustment = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('product', 'size', 'color')
    
    def __str__(self):
        return f"{self.product.name} - {self.size} {self.color}"


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} x {self.quantity}"
    
    def get_total_price(self):
        price = self.product.price
        if self.variant:
            price += self.variant.price_adjustment
        return price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_amount = models.IntegerField()
    discount_amount = models.IntegerField(default=0)
    final_amount = models.IntegerField()
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    payment_method = models.CharField(max_length=50, default='COD')
    tracking_number = models.CharField(max_length=100, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    shipping_address = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - ₹{self.final_amount}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=200)
    product_price = models.IntegerField()
    quantity = models.IntegerField()
    variant_info = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    helpful_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}⭐"


class ProductLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.username} likes {self.product.name}"


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.IntegerField()
    min_purchase_amount = models.IntegerField(default=0)
    max_discount_amount = models.IntegerField(null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    usage_limit = models.IntegerField(default=1)
    used_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'percentage' else '₹'}"
    
    def is_valid(self):
        from django.utils import timezone
        return (
            self.is_active and
            self.valid_from <= timezone.now() <= self.valid_until and
            self.used_count < self.usage_limit
        )
    
    def calculate_discount(self, amount):
        if self.discount_type == 'percentage':
            discount = (amount * self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.discount_value
        return min(discount, amount)


class RecentlyViewed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recently_viewed')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-viewed_at']
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    avatar = models.URLField(blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
