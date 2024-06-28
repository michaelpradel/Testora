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
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_pull_requests_count(owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls'
    params = {
        'state': 'all',
        'per_page': 100,
        'page': 1
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    total_prs = 0
    total_prs += len(response.json())

    while 'next' in response.links:
        response = requests.get(response.links['next']['url'], headers=headers)
        response.raise_for_status()
        total_prs += len(response.json())

    return total_prs


def main():
    query = 'language:Python'
    repositories = search_repositories(query)['items']

    out_file = "candidate_projects.csv"
    with open(out_file, mode='w', newline='') as out_fp:
        writer = csv.writer(out_fp)
        writer.writerow(['Name', 'PRs', 'Description'])

    for repo in repositories:
        repo_full_name = repo['full_name']
        repo_description = repo['description']
        pr_count = get_pull_requests_count(*repo_full_name.split('/'))
        print(f'{repo_full_name} -- {pr_count} -- {repo_description}')
        with open(out_file, mode='a', newline='') as out_fp:
            writer = csv.writer(out_fp)
            writer.writerow([repo_full_name, pr_count, repo_description])
            out_fp.flush()


if __name__ == "__main__":
    main()
