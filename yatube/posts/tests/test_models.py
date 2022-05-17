from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='auth')
        self.group = Group.objects.create(
            title='Test group',
            slug='test_slug',
            description='Test description',
        )
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый пост тестовый пост тестовый пост',
        )

    def test_verbose_name(self):
        field_verboses = {
            'text': 'Текст',
            'group': 'Группа',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                self.assertEqual(
                    self.post._meta.get_field(value).verbose_name, expected
                )

    def test_help_text(self):
        field_help_texts = {
            'text': 'Отредактируйте или введите новый текст',
            'group': 'Группа, к которой будет относиться пост',
        }
        for value, expected in field_help_texts.items():
            with self.subTest(value=value):
                self.assertEqual(
                    self.post._meta.get_field(value).help_text, expected
                )

    def test_author_is_user(self):
        self.assertEqual(self.user, self.post.author)

    def test_object_name_is_text_field(self):
        expected_object_name = self.post.text[:15]
        self.assertEqual(expected_object_name, str(self.post))

    def test_group_name_is_title(self):
        expected_object_name = self.group.title
        self.assertEqual(expected_object_name, str(self.group))
