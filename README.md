git-code-golf
===

A minimal script to version control your [code.golf](https://code.golf) solutions.

## Requirements

- git
- Python 3

No module other than the Python standard library is required.

## Usage

```
python3 git-code-golf.py -a AUTHORIZATION -o OUTPUT
```

Where:
- `AUTHORIZATION` is your session token UUID; you can find it by looking at the cookies and looking for `__Host-session`
- `OUTPUT` the path to the repository where the solutions will be stored

You can list the available options using:
```
python3 git-code-golf.py -h
```

## Disclaimer

Unlike other challenge platforms that focus on learning, code.golf is a competitive website. This means that participants are competing against each other fairly. Therefore, to keep it fun for everyone please do not reveal your solutions publicly.

If you would like to learn about code golf and see other people's solutions, the [Stack Exchange](https://codegolf.stackexchange.com/) is a great place for that.
