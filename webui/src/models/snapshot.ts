export type TimelapseSnapshot = {
    'commit_sha': string;
    'commit_date': number;
    'status': { [key: string]: string };
    'error': string;
    'includes': string[],
    'gitDiff': string,
    'changed_pages': number[],
    'pages': []
}
