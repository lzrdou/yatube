import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='user_test')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(
            title='test group',
            slug='test-slug',
            description='test description',
        )
        self.group_for_edit = Group.objects.create(
            title='test edit group',
            slug='test-edit-slug',
            description='test edit description',
        )
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group,
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=(
                b'\x47\x49\x46\x38\x39\x61\x02\x00'
                b'\x01\x00\x80\x00\x00\x00\x00\x00'
                b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                b'\x0A\x00\x3B'
            ),
            content_type='image/gif'
        )

    def test_create_post(self):
        post_count = Post.objects.count()
        form_data = {
            'text': 'Test post',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.user.username}
            )
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.author, self.user)

    def test_post_edit(self):
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост измененный',
            'group': self.group_for_edit.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        post = Post.objects.filter(pk=self.post.id).get()
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.author, self.user)

    def test_cant_create_empty_post(self):
        post_count = Post.objects.count()
        form_data = {
            'text': '',
            'group': self.group_for_edit.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertFormError(
            response,
            'form',
            'text',
            'Обязательное поле.'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK.value)

    def test_guest_cant_create_post(self):
        post_count = Post.objects.count()
        form_data = {
            'text': 'Test cant create post',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        expected_url = (
            reverse('users:login')
            + '?next='
            + reverse('posts:post_create')
        )
        self.assertRedirects(response, expected_url)

    def test_comment(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Test comment'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        comment = self.post.comments.first()
        self.assertEqual(comment.text, form_data['text'])

    def test_guest_cant_comment(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Test comment'
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count)
        expected_url = (
            reverse('users:login')
            + '?next='
            + reverse('posts:add_comment', kwargs={'post_id': self.post.id})
        )
        self.assertRedirects(response, expected_url)

    def test_image_post_created(self):
        post_count = Post.objects.count()
        form_data = {
            'text': 'Test image post',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.user.username}
            )
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.image, 'posts/small.gif')
