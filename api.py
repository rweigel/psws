import django.urls
import django.http

def hello_world(request):
    # collect query params (preserve multiple values)
    params = {}
    for k in request.GET.keys():
        vals = request.GET.getlist(k)
        params[k] = vals if len(vals) > 1 else vals[0]
    print(f"Query parameters: {params}")
    return django.http.JsonResponse({'message': 'Hello, World!', 'query': params})

# URL configuration
urlpatterns = [
    django.urls.path('', hello_world, name='hello_world')
]
