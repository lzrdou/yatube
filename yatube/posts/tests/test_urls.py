from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):

    def setUp(self):
        self.guest_client = Client()
        self.user1 = User.objects.create_user(username='user_test')
        self.user2 = User.objects.create_user(username='test_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user1)
        self.group = Group.objects.create(
            title='Test group',
            slug='test_slug',
            description='Test description',
        )
        self.post1 = Post.objects.create(
            author=self.user1,
            text='Тестовый пост 1',
        )
        self.post2 = Post.objects.create(
            author=self.user2,
            text='Тестовый пост 2'
        )

    def tearDown(self):
        cache.clear()

    def test_common_pages(self):
        tested_urls = {
            '/': HTTPStatus.OK.value,
            f'/group/{self.group.slug}/': HTTPStatus.OK.value,
            f'/profile/{self.user1.username}/': HTTPStatus.OK.value,
            f'/posts/{self.post1.pk}/': HTTPStatus.OK.value,
            '/unexisting_page/': HTTPStatus.NOT_FOUND.value
        }
        for url, expected_resp_code in tested_urls.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, expected_resp_code)

    def test_create_post_page(self):
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)

    def test_edit_post_author(self):
        response = self.authorized_client.get('/posts/1/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK.value)

    def test_edit_post_not_author(self):
        response = self.authorized_client.get('/posts/2/edit/', follow=True)
        self.assertRedirects(response, '/posts/2/')

    def test_urls_uses_correct_templates(self):
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user1.username}/': 'posts/profile.html',
            f'/posts/{self.post1.pk}/': 'posts/post_detail.html',
            f'/posts/{self.post1.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template, f'{template}')
