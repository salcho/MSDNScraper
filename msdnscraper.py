import requests
from lxml import html
import re
import sys

known_types = {'https://msdn.microsoft.com/en-us/library/system.string(v=vs.110).aspx': 'mscorlib'}

def get_assembly_html(html):
    assembly = html.xpath('//*[@id="mainBody"]/div/text()[2]')[0].encode('ascii', 'ignore')
    assembly = assembly.split(' ')
    return re.match(r'(.*)\.dll', assembly[len(assembly) - 1]).group(1)

def get_assembly(url):
    if known_types.has_key(url):
        return known_types[url]
    page = requests.get(url, verify = False)
    return get_assembly_html(html = html.fromstring(page.content))

def build_signature(tree):
    ret = get_return_type(tree)
    namespace = tree.xpath('//*[@id="mainBody"]/div/a[1]/text()')[0]
    assembly = get_assembly_html(tree)
    method = get_method_name(tree)
    args = get_params(tree)
    classname = get_class_name(tree)

    # TODO: Fix me. I suck.
    code_snippets = tree.xpath('//*[starts-with(@id, "CodeSnippetContainerCode_")]/div/pre/span[2]/text()')
    if len(code_snippets) == 0:
        is_static = False       # default to instance because we can
    else:
        is_static = True if 'static' in code_snippets else False

    return '%s %s [%s]%s.%s%s(%s)' % (
        'static' if is_static and found_method(method) else '',  # is it static? ignore this if it is a ctor
        ret if found_method(method) else '',  # did we find a method name?
        assembly,
        namespace,
        classname,
        method,
        ''.join(args)
    )

def found_method(name):
    return '::' in name

def get_method_name(tree):
    method = tree.xpath('/html/head/title/text()')[0]
    if ' Method ' in method:
        method = '::%s' % method.split(' Method')[0].split('.')[-1]
    elif ' Constructor ' in method:
        method = '.%s' % method.split(' Constructor')[0]
    else:
        raise Exception('I dunno this type bro: ' + method)
    return method

def get_params(tree):
    i = 1
    args = ''
    while (True):
        value = tree.xpath('//*[@id="mainBody"]/div/div[2]/div/div[2]/dl[%d]/dt/span/text()' % i)
        paramTypeQuery = '//*[@id="mainBody"]/div/div[2]/div/div[2]/dl[%d]/dd/span/a/%s'
        type = tree.xpath(paramTypeQuery % (i, 'text()'))
        if len(value) == 0 or len(type) == 0:
            break
        args = '%s[%s]%s %s, ' % (
            args,
            get_assembly(url = tree.xpath(paramTypeQuery % (i, '@href'))[0]),
            type[0].strip(),
            value[0].strip()
        )
        i += 1
    args = args[:len(args) - 2]
    return args

def get_return_type(tree):
    returnPath = '//*[@id="mainBody"]/div/div[2]/div/div[3]/span/a/'
    ret = tree.xpath(returnPath + 'text()')
    if len(ret) == 0:
        ret = 'void'
    else:
        returnAssembly = get_assembly(url=tree.xpath(returnPath + '@href')[0])
        ret = '[%s]%s' % (returnAssembly, ret[0])
    return ret

def get_links(html, max):
    urls = []
    get_constructors(html, urls)
    get_methods(max, html, urls)
    return urls

def get_class_name(tree):
    return tree.xpath('//*[@id="content"]/div[2]/div/h1/text()')[0].split(' ')[0]

def get_tree(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    return tree

def get_methods(max, tree, urls):
    for i in range(2, max):
        urls.append(tree.xpath('//*[@id="idMethods"]/tbody/tr[%s]/td[2]/a/@href' % i)[0])

def get_constructors(tree, urls):
    i = 2
    while (True):
        row = tree.xpath('//*[@id="idConstructors"]/tbody/tr[%d]/td[2]/a/@href' % i)
        if len(row) == 0:
            break
        urls.append(row[0])
        i += 1

def main(url, max = 5):
    #tree = get_tree('https://msdn.microsoft.com/en-us/library/system.io.directoryinfo(v=vs.110).aspx')
    tree = get_tree(url)
    urls = get_links(html= tree, max = max)

    signatures = ''
    for url in urls:
        signatures = '%s\n%s' % (signatures, build_signature(tree= get_tree(url)))

    return signatures

if len(sys.argv) < 3:
    print 'Usage: %s <max-methods-per-class> <url to MSDN class>...'
    exit()

signatures = ''
for arg in sys.argv[2:]:
    signatures = '%s\n%s' % (signatures, main(arg, max = int(sys.argv[1])))
print signatures

#main('https://msdn.microsoft.com/en-us/library/system.data.sqlclient.sqlconnection(v=vs.110).aspx', max = 7)
#main('https://msdn.microsoft.com/en-us/library/system.xml.linq.xdocument(v=vs.110).aspx', max = 7)
#main('https://msdn.microsoft.com/en-us/library/system.diagnostics.processstartinfo(v=vs.110).aspx', max = 7)