import os
import re

repos_path = "../repos/";
todos_files = ("/deshi.cpp", "/atmos.cpp", "/suugu.cpp", "/go.cpp", "/fukushi.cpp")

def find_files(dir_name,ext):
    filepaths = [];
    for dirpath,dirnames,filename in os.walk(dir_name):
        for file in filename:
            filepath = "%s/%s"%(dirpath.replace("\\","/"),file);
            if isinstance(ext, (list, tuple)):
                for e in ext:
                    if filepath.endswith(e):
                        filepaths.append(filepath);
            else:
                if filepath.endswith(ext):
                    filepaths.append(filepath);
    return filepaths;

def main():
    #get c/c++ files
    files = find_files(repos_path, [".h", ".c", ".hpp", ".cpp", ".inl"]);

    #iterate only the main .cpp files to check for todos
    todos = []; #(project str, group str, date str, difficulty str, arr of tag strs, desc)
    for file_path in (_ for _ in files if _.endswith(todos_files)):
        project = file_path[file_path.rfind('/')+1 : file_path.rfind('.')];
        #print(file_path, project); continue;

        #open file and read to string
        contents = "";
        with open(file_path, mode="r", encoding="utf8") as file:
            contents = file.read();
        if contents == "":
            print("Failed to open file: ", file_path);
            continue;

        #perform regex searches
        comments = list(re.finditer(r"(?<=\/\*)(.|\n)*?(?=\*\/)", contents));
        tags     = list(re.finditer(r"(?<=\`).*?(?=\`)",          contents));
        squares  = list(re.finditer(r"(?<=\[).*?(?=\])",          contents));
        if (len(comments) == 0) or (len(tags) == 0) or (len(squares) == 0): continue;
        #print(file_path); print(comments); print(tags); print(squares, "\n"); continue;

        #find the todos comment block
        todos_comment_start = -1;
        todos_comment_end   = -1;
        for tag in tags:
            if tag.group() != "TODO": continue;
            for i,comment in enumerate(comments):
                if comment.start() < tag.start() < comment.end():
                    todos_comment_start = comment.start();
                    todos_comment_end   = comment.end();
                    break;
            if not todos_comment_start == -1: break;
        if (todos_comment_start == -1) or (todos_comment_end == -1): continue;
        #print(project, "\n", contents[todos_comment_start:todos_comment_end], "\n"); continue;

        #find todo groups
        groups = []; #(name str, start idx)
        for tag in tags:
            if (tag.group() != "TODO") and (todos_comment_start < tag.start() < todos_comment_end):
                groups.append((tag.group(), tag.start()-1));
                #print(project, tag.group());

        #find todo headers
        headers = []; #(group str, date str, difficulty str, arr of tag strs, header start idx, desc start idx, )
        for square in squares:
            if todos_comment_end < tag.start() < todos_comment_start: continue;
            for group in reversed(groups):
                if square.start() < group[1]: continue;
                split = square.group().split(",");
                if   len(split) == 0:
                    headers.append((group[0], "?",              "?",              [],                             
                                    square.start()-1, square.end()+2));
                elif len(split) == 1:
                    headers.append((group[0], split[0].strip(), "?",              [],                             
                                    square.start()-1, square.end()+2));
                elif len(split) == 2:
                    headers.append((group[0], split[0].strip(), split[1].strip(), [],                             
                                    square.start()-1, square.end()+2));
                elif len(split) > 2:
                    headers.append((group[0], split[0].strip(), split[1].strip(), [s.strip() for s in split[2:]], 
                                    square.start()-1, square.end()+2));
                #print(headers[-1]);
                break;

        #fill todos
        for i,header in enumerate(headers):
            if i == len(headers)-1:
                desc_end = todos_comment_end;
                while (contents[desc_end] == ' ') or (contents[desc_end] == '\r') or (contents[desc_end] == '\n'): desc_end -= 1;
                todos.append((project, header[0], header[1], header[2], header[3], 
                              contents[header[5] : desc_end].strip()));
            elif headers[i][0] != headers[i+1][0]:
                desc_end = headers[i+1][4];
                while contents[desc_end] != '`': desc_end -= 1; desc_end -= 1;
                while contents[desc_end] != '`': desc_end -= 1; desc_end -= 1;
                while (contents[desc_end] == ' ') or (contents[desc_end] == '\r') or (contents[desc_end] == '\n'): desc_end -= 1;
                todos.append((project, header[0], header[1], header[2], header[3], 
                              contents[header[5] : desc_end+1].strip()));
            else:
                desc_end = headers[i+1][4];
                while (contents[desc_end] == ' ') or (contents[desc_end] == '\r') or (contents[desc_end] == '\n'): desc_end -= 1;
                todos.append((project, header[0], header[1], header[2], header[3], 
                              contents[header[5] : desc_end].strip()));
            #print(todos[-1]);

if __name__ == "__main__": main();