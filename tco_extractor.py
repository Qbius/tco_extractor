import codecs
from urllib.request import urlopen
from re import finditer, search
from itertools import chain
from time import sleep
from sys import stdout
from os.path import exists, dirname, join
from os import mkdir

output_dir = join(dirname(__file__), "tco_extractor")

def create_dir(full_path):
    if not exists(full_path):
        mkdir(full_path)

def print_no_newline(msg):
    stdout.write(msg)
    stdout.flush()
    
def print_same_line(msg):
    stdout.write('\r')
    stdout.write(msg)
    stdout.flush()
    
def progress_bar(raw_percentage):
    proper_percentage = round(100 * raw_percentage)
    tens = proper_percentage // 5
    return str(proper_percentage).rjust(3) + "% [" + "".join(["|"] * tens) + "".join(["."] * (20 - tens)) + "]"
    
def string_segment(str, cut_to, cut_from):
    return str.split(cut_to)[1].split(cut_from)[0] if cut_to in str and cut_from in str else str
    
def find_last_page(content):
    last_page_regex = search("page=([0-9]+).+ title=\"go to last page\"", content)
    if last_page_regex:
        return int(last_page_regex.groups()[0])
    else:
        available_pages = [int(found.groups()[0]) for found in finditer("([0-9]+)</a>", string_segment(content, "Pages:", "</td>"))]
        return max(available_pages) if len(available_pages) > 0 else 1
    
def get_content(author_name, page_number = 1):
    return urlopen("http://www.tradecardsonline.com/?action=selectCard&goal=DK&game_id=33&filter_author=%s&page=%s" % (author_name, str(page_number))).read().decode()
    
def get_decks_info(content):
    return [(found.group("deck_name"), found.group("deck_id")) for found in finditer("<a href=\"/im/showDeck/deck_id/(?P<deck_id>[0-9]+)\">(?P<deck_name>.+)</a>", content)]

def get_all_decks_info(author_name):
    last_page_number = find_last_page(get_content(author_name))
    return list(chain(*[get_decks_info(get_content(author_name, page_number)) for page_number in range(1, last_page_number + 1)]))

def get_civilization_segments(content):
    civ_info = [(found.group("civ_name"), found.group("civ_count")) for found in finditer("<strong>Civilization: (?P<civ_name>.+) \((?P<civ_count>[0-9]+) cards\)</strong>", content)]
    return {civ_name: (civ_count, string_segment(content, "<strong>Civilization: %s (%s cards)</strong>" % (civ_name, civ_count), "<!-- extended_format -->")) for civ_name, civ_count in civ_info}
    
def get_cards(content):
    names = [found.groups()[0] for found in finditer("onMouseout=\"hideSmallImage\(\);\">(.+)</a>", content)]
    amounts = [int(found.groups()[0]) for found in finditer("<strong>([0-9]+)</strong>", content)]
    return ["%dx %s" % (amount, name) for amount, name in zip(amounts, names)]
    
def get_deck_content(id):
    content = urlopen("http://www.tradecardsonline.com/im/showDeck/deck_id/%s&extended_format=&grouping=col_01" % id).read().decode()
    list_segment = string_segment(content, "cell_padded_4 deck_section_table", "</table>")
    raw_civ_card_list = [(civ_name, civ_count, get_cards(civ_content)) for civ_name, (civ_count, civ_content) in get_civilization_segments(list_segment).items()]
    multi_count = str(sum([int(count) for _, count, _ in filter(lambda tup: '/' in tup[0], raw_civ_card_list)]))
    multi_cards = list(chain(*[cards for _, _, cards in filter(lambda tup: '/' in tup[0], raw_civ_card_list)]))
    civ_cards = [("%s: %s\r\n" % (civ_name, civ_count)) + '\r\n'.join(civ_cards) for civ_name, civ_count, civ_cards in list(filter(lambda tup: '/' not in tup[0], raw_civ_card_list)) + ([("Multi", multi_count, multi_cards)] if int(multi_count) > 0 else [])]
    return '\r\n\r\n'.join(civ_cards) + "\r\n\r\nTOTAL: " + str(sum([int(count) for _, count, _ in raw_civ_card_list]))
    
def save_deck_to_disk(path, name, id):
    for character in "/<>:\"/\\|?*":
        name = name.replace(character, "_")
     
    with codecs.open(join(path, name + ".txt"), "w", "utf-8-sig") as output_file:
        output_file.write(get_deck_content(id))
        
def handle_author(author_name):   
    print_no_newline("checking %s... " % author_name)
    decks = get_all_decks_info(author_name)
    decks_count = len(decks)
    
    if decks_count > 0:
        print_no_newline("%d decks found. " % decks_count)
        sleep(0.9)
        print_no_newline("Downloading...")
        sleep(0.9)
        print()
        author_dir = join(output_dir, author_name)
        create_dir(author_dir)
        for i, (deck_name, deck_id) in enumerate(decks):
            print_same_line(("%s %s" % (progress_bar(i / decks_count), deck_name)).ljust(80))
            save_deck_to_disk(author_dir, deck_name, deck_id)
        
        print_same_line(("%s %s" % (progress_bar(1), "Complete!")).ljust(80))
        print()
    else:
        print("No decks found.")

def handle_authors(authors):
    create_dir(output_dir)
    [handle_author(author) for author in authors]
    
handle_authors(input("One or more TCO nicknames, separated by spaces: ").split())
input("Done. Check the \"tco_extractor\" directory. Press any key to continue...")