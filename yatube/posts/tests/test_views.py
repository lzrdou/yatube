import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsURLTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user1 = User.objects.create_user(username='user_test')
        self.user2 = User.objects.create_user(username='test_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user1)
        self.group = Group.objects.create(
            title='test group',
            slug='test-slug',
            description='test description',
        )
        self.post1 = Post.objects.create(
            author=self.user1,
            text='Тестовый пост 1',
        )
        self.post2 = Post.objects.create(
            author=self.user2,
            text='Тестовый пост с группой и картинкой',
            group=self.group,
            image=SimpleUploadedFile(
                name='test_image.jpg',
                content=(
                    b'\x47\x49\x46\x38\x39\x61\x02\x00'
                    b'\x01\x00\x80\x00\x00\x00\x00\x00'
                    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                    b'\x0A\x00\x3B'
                ),
                content_type='image/jpeg'
            )
        )

    def tearDown(self):
        cache.clear()

    def test_pages_use_correct_template(self):
        template_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}):
                    'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.user1.username}):
                    'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post1.id}):
                    'posts/post_detail.html',
            reverse(
                'posts:post_create'):
                    'posts/create_post.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post1.id}):
                    'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in template_pages_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_shows_correct_context(self):
        response = self.guest_client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        self.assertEqual(response.context['page_obj'][0], self.post2)

    def test_group_posts_shows_correct_context(self):
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertIn('group', response.context)
        self.assertIn('page_obj', response.context)
        self.assertEqual(response.context['page_obj'][0], self.post2)
        self.assertEqual(response.context['group'], self.group)

    def test_profile_shows_correct_context(self):
        response = self.guest_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user2.username})
        )
        self.assertIn('author', response.context)
        self.assertIn('page_obj', response.context)
        self.assertIn('post_num', response.context)
        self.assertEqual(response.context['page_obj'][0], self.post2)
        self.assertEqual(
            response.context['post_num'],
            self.user2.posts.all().count()
        )
        self.assertEqual(response.context['author'], self.user2)

    def test_post_detail_shows_correct_context(self):
        response = self.guest_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post2.id})
        )
        self.assertIn('post', response.context)
        self.assertIn('post_num', response.context)
        self.assertEqual(response.context['post'], self.post2)
        self.assertEqual(
            response.context['post_num'],
            self.user2.posts.all().count()
        )

    def test_post_create_shows_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_shows_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post1.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context['post'], self.post1)

    def test_cache_page_is_used(self):
        response = self.guest_client.get(reverse('posts:index'))
        self.post1.delete()
        self.assertIn(self.post1.text.encode('utf-8'), response.content)
        cache.clear()
        response = self.guest_client.get(reverse('posts:index'))
        self.assertNotIn(self.post1.text.encode('utf-8'), response.content)

    def test_auth_user_follow_unfollow(self):
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user2.username}
            )
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.user1,
                author=self.user2
            ).exists()
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user2.username}
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.user1,
                author=self.user2
            ).exists()
        )

    def test_follow_index(self):
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user2.username}
            )
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(self.post2, response.context['page_obj'])
        authorized_client = Client()
        authorized_client.force_login(self.user2)
        response = authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(self.post2, response.context['page_obj'])


def num_of_obj_on_page(obj_qnt, obj_per_page, page_num):
    if obj_qnt / obj_per_page >= page_num:
        expected_obj_qnt = obj_per_page
    else:
        expected_obj_qnt = obj_qnt - obj_per_page
    return expected_obj_qnt


class PaginatorViewsTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user_test')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user1)
        self.group = Group.objects.create(
            title='test group',
            slug='test-slug',
            description='test description',
        )
        self.posts = [
            Post.objects.create(
                author=self.user1, group=self.group) for _ in range(13)
        ]

    def test_first_index_page_ten_records(self):
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(
            len(response.context['page_obj']),
            settings.POSTS_PER_PAGE
        )

    def test_second_index_page_three_records(self):
        response = self.authorized_client.get(
            reverse('posts:index') + '?page=2'
        )
        expected_obj_qnt = num_of_obj_on_page(
            len(self.posts), settings.POSTS_PER_PAGE, 2
        )
        self.assertEqual(len(response.context['page_obj']), expected_obj_qnt)

    def test_first_group_page_ten_records(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(
            len(response.context['page_obj']),
            settings.POSTS_PER_PAGE
        )

    def test_second_group_page_three_records(self):
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )
            + '?page=2'
        )
        expected_obj_qnt = num_of_obj_on_page(
            len(self.posts), settings.POSTS_PER_PAGE, 2
        )
        self.assertEqual(len(response.context['page_obj']), expected_obj_qnt)

    def test_first_profile_page_ten_records(self):
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user1.username})
        )
        self.assertEqual(
            len(response.context['page_obj']),
            settings.POSTS_PER_PAGE
        )

    def test_second_profile_page_three_records(self):
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user1.username}) + '?page=2')
        expected_obj_qnt = num_of_obj_on_page(
            len(self.posts), settings.POSTS_PER_PAGE, 2
        )
        self.assertEqual(len(response.context['page_obj']), expected_obj_qnt)
