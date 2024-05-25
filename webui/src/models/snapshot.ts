export type TimelapseSnapshot = {
    'commit_sha': string;
    'commit_date': number;
    'status': { [key: string]: string };
    'error': string;
    'includes': number[],
    'gitDiff': string,
    'changed_pages': number[],
    'pages': []
}
