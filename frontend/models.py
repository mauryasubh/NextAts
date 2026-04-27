from django.db import models

class ContactRequest(models.Model):
    """
    Stores leads from the 'Contact Sales' form.
    """
    name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.company_name}"
