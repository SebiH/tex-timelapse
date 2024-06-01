export type TimelapseSnapshot = {
    'commit_sha': string;
    'commit_date': number;
    'main_tex_file': string;
    'status': { [key: string]: string };
    'error': string;
    'includes': string[],
    'gitDiff': string,
    'changed_pages': { page: number, x1: number, y1: number, x2: number, y2: number }[],
    'pages': []
}
