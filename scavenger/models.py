from django.db import models


# Create your models here.
class Hunt(models.Model):
    name = models.TextField()
    final_password = models.TextField()
    riddles = models.ManyToManyField("Riddle", related_name="hunts", null=True, blank=True)

    def __str__(self):
        return self.name


class Kiosk(models.Model):
    hunt = models.ForeignKey(Hunt, related_name="kiosks", on_delete=models.CASCADE)
    location = models.TextField()


class Team(models.Model):
    hunt = models.ForeignKey("Hunt", on_delete=models.CASCADE)
    name = models.TextField()
    solved = models.ManyToManyField("Riddle", related_name="+")
    final_password_order = models.TextField()
    final_password_progression = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Riddle(models.Model):
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return self.question
