import inspect
import os
import random
import readline
import shutil
import string
import subprocess
import tempfile
import signal

import completer
import entrydao
from entry import Entry, EntryNotFoundError

DEFAULT_HEADER_SIZE = 2


def prompt_warning(func):
    func.prompt_warning = True
    return func


def datetime_str_default(datetime):
    return f"({datetime:%Y-%m-%d:%H.%M})"


def get_user_input(text_in=""):
    with tempfile.NamedTemporaryFile() as buffer:
        buffer_path = buffer.name

        with open(buffer_path, "w") as f:
            f.write(text_in)

        cmd = ["vim", buffer_path]
        subprocess.run(cmd)

        with open(buffer_path, "r") as f:
            text_out = f.read()
    return text_out


def entry_from_user_input(text, header_size=DEFAULT_HEADER_SIZE):
    """header lines are ignored """
    lines = text.split("\n")
    new_text = "\n".join(lines[header_size:])
    return Entry(new_text)


def make_header(creation_datetime):
    datetime_str = datetime_str_default(creation_datetime)
    line = f"created: {datetime_str}"
    bar = "~" * len(line)
    return f"{line}\n{bar}"


def entry_to_user_input(entry):
    template = "{header}\n{body}"
    return template.format(body=entry.text, header=make_header(entry.datetime))


def show_text_beginning(text, max_n_char=32, going_on="..."):
    cut = text[:max_n_char + 1].replace("\n", " ")
    end = going_on if len(cut) > max_n_char else ""
    s = cut[:max_n_char - len(end)] + end
    return f"{s:<{max_n_char}}"


def write_new(dao):
    entry_new = entry_from_user_input(get_user_input(entry_to_user_input(Entry())))
    dao.write(entry_new)


def update(dao, id_entry):
    entry_old = dao.get(id_entry)
    if entry_old is None:
        print(f"Entry with id {id_entry} not found")
        return
    entry_new = entry_from_user_input(get_user_input(entry_to_user_input(entry_old)))
    dao.update(id_entry, entry_new)


def list_entries(dao):
    for id, entry in dao.get_all():
        print(f"{id}|", show_text_beginning(entry.text.strip()), datetime_str_default(entry.datetime), f"|{id}")


def show(id_entry, dao):
    entry = dao.get(id_entry)
    if entry is not None:
        n = max([len(line) for line in entry.text.split("\n")])
        print("=" * n)
        print(entry.text.strip())
        print("=" * n)
    else:
        print(f"Entry with id {id_entry} not found")


@prompt_warning
def delete(id_entry, dao):
    nb_row_deleted = dao.delete(id_entry)
    print(f"nb of rows deleted: {nb_row_deleted}")


@prompt_warning
def reset(dao):
    shutil.rmtree(os.path.dirname(entrydao.db_path_default))
    dao.init_table()


def help(actions):
    print("/".join([sorted(aliases, key=len)[0] for action, aliases in actions.items()]))


def write_random_entry(dao, text_size=64):
    chars = " " + string.ascii_lowercase
    text = "".join(random.choices(chars, weights=[8] + [1 for _ in string.ascii_lowercase], k=text_size))
    dao.write(Entry(text))


actions = {
    help: ["h", "help"],
    list_entries: ["list", "l"],
    show: ["s", "show"],
    update: ["update", "u"],
    write_new: ["new", "n"],
    write_random_entry: ["random"],
    delete: ["delete", "d"],
    reset: ["reset"]
}


def get_check_id_entry(ans_tail):
    input_entry = ans_tail[0] if len(ans_tail) > 0 else input("entry id?")
    try:
        return int(input_entry)
    except ValueError:
        raise ValueError(f"Expected integer, unlike: {input_entry}")


def loop(actions, dao):
    while True:
        ans = input()
        ans_splitted = ans.split()
        ans_head = ans_splitted[0] if len(ans_splitted) > 0 else None
        ans_tail = ans_splitted[1:]
        for action, aliases in actions.items():
            if ans_head in aliases:
                if getattr(action, "prompt_warning", False):
                    if input("Are you sure? (y/*)") != "y":
                        print("nothing happened")
                        continue
                expected_args = inspect.getfullargspec(action)[0]
                getters = {
                    "dao": lambda: dao,
                    "id_entry": lambda: get_check_id_entry(ans_tail),
                    "actions": lambda: actions,
                }
                try:
                    selected_items = {name: getter() for name, getter in getters.items() if name in expected_args}
                    action(**selected_items)
                except ValueError as e:
                    print(e)
                except EntryNotFoundError as e:
                    print(e)

        if ans_head in ("quit", "q"):
            break


def exit_handler(sig, frame):
    print("\nbye")
    exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, exit_handler)

    options = [sorted(x, key=len)[-1] for x in actions.values()]
    readline.set_completer(completer.Completer(options).complete)
    readline.parse_and_bind('tab: complete')

    loop(actions, entrydao.EntryDao())

