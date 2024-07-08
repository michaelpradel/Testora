import requests
import csv

with open(".github_token") as f:
    github_token = f.read().strip()
headers = {'Authorization': f'token {github_token}'}


def search_repositories(query, sort='stars', order='desc', per_page=100):
    url = 'https://api.github.com/search/repositories'
    params = {
        'q': query,
        'sort': sort,
        'order': order,
        'per_page': per_page
    }
    print(".")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def fetch_top_python_repos(total_repos=1000, per_page=100):
    url = 'https://api.github.com/search/repositories'

    params = {
        'q': 'language:Python',
        'sort': 'stars',
        'order': 'desc',
        'per_page': per_page,
        'page': 1
    }

    repos = []

    while len(repos) < total_repos:
        print(".")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()

        repos.extend(data['items'])

        if 'next' not in response.links:
            break

        params['page'] += 1

    return repos[:total_repos]


def get_pull_requests_count_graphql(owner, repo):
    url = 'https://api.github.com/graphql'

    query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        pullRequests {
          totalCount
        }
      }
    }
    """

    variables = {
        'owner': owner,
        'repo': repo
    }

    print(".")
    response = requests.post(
        url, json={'query': query, 'variables': variables}, headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors

    data = response.json()
    total_prs = data['data']['repository']['pullRequests']['totalCount']

    return total_prs


def get_pull_requests_count(owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls'
    params = {
        'state': 'all',
        'per_page': 100,
        'page': 1
    }
    print(".")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    total_prs = 0
    total_prs += len(response.json())

    while 'next' in response.links:
        print(".")
        response = requests.get(response.links['next']['url'], headers=headers)
        response.raise_for_status()
        total_prs += len(response.json())

    return total_prs


def main():
    query = 'language:Python'
    # repositories = search_repositories(query)['items']
    repositories = fetch_top_python_repos()

    out_file = "candidate_projects2.csv"
    with open(out_file, mode='w', newline='') as out_fp:
        writer = csv.writer(out_fp)
        writer.writerow(['Name', 'Stars', 'PRs', 'Description'])

    print(f"Found {len(repositories)} repositories")
    for repo in repositories:
        repo_full_name = repo['full_name']
        repo_description = repo['description']
        if not repo_description or "library" not in repo_description.lower():
            print(
                f'Skipping {repo_full_name} because it seems to not be a library')
            continue
        print(f"Counting PRs for {repo_full_name}")
        pr_count = get_pull_requests_count_graphql(*repo_full_name.split('/'))
        stars = repo['stargazers_count']
        print(f'{repo_full_name} -- {stars} -- {pr_count} -- {repo_description}')
        with open(out_file, mode='a', newline='') as out_fp:
            writer = csv.writer(out_fp)
            writer.writerow([repo_full_name, stars, pr_count, repo_description])
            out_fp.flush()


if __name__ == "__main__":
    main()
