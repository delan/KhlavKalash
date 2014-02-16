from plugins.categories import ISilentCommand

import regex
import copy

class Sedbot (ISilentCommand):
    triggers = {
        r'(.*)': "sed"
    }

    # I planned to have separate triggers for tracking the last message and
    # invoking a replacement, but this requires the replacement trigger to
    # always be reached before the tracking trigger on iteration, which is
    # not guaranteed as a dict is an unordered data structure.

    def __init__(self):
        self.last = None

    def trigger_sed(self, user, channel, match):
        message = match.group(1).decode('utf-8')
        if regex.match(r'^s/.*/.*/.*$', message):
            if 'James_T' in user:
                return
            if self.last is not None:
                sed_objs = self.parse(message)
                if sed_objs is not None:
                    for sed_obj in sed_objs:
                        flags = 0
                        if sed_obj['flags']['insensitive']:
                            flags |= regex.IGNORECASE
                        # TODO: global and offset flag handling
                        # doesn't appear to be possible with the python re API
                        # ...at least not in a simple regex.sub() call
                        self.last = regex.sub(
                            sed_obj['needle'],
                            sed_obj['replacement'],
                            self.last,
                            flags=flags
                        )
                    return self.last
        else:
            self.last = message

    @staticmethod
    def parse(expr):
        def error(i, message):
            print 'sed parse error: %d: %s' % (i, message)
        def skeleton():
            return copy.copy({
                'needle': '',
                'replacement': '',
                'flags': {
                    'global': False,
                    'insensitive': False,
                    'offset': 1
                }
            })
        def skelhits():
            return copy.copy({
                'start': 0,
                'ready': 0,
                'needle': 0,
                'needle_backslash': 0,
                'replacement': 0,
                'replacement_backslash': 0,
                'flags': 0,
                'flags_offset': 0
            })
        state = 'start'
        result = []
        out = skeleton()
        hits = skelhits()
        for i, c in enumerate(expr):
            hits[state] += 1
            if state == 'start':
                if c == 's':
                    state = 'ready'
                else:
                    return error(i, 'expected "s"')
            elif state == 'ready':
                if c == '/':
                    state = 'needle'
                else:
                    return error(i, 'expected "/"')
            elif state == 'needle':
                if c == '/':
                    state = 'replacement'
                elif c == '\\':
                    state = 'needle_backslash'
                else:
                    out['needle'] += c
            elif state == 'needle_backslash':
                if c == '/':
                    out['needle'] += '/'
                else:
                    out['needle'] += '\\' + c
                state = 'needle'
            elif state == 'replacement':
                if c == '/':
                    state = 'flags'
                elif c == '\\':
                    state = 'replacement_backslash'
                else:
                    out['replacement'] += c
            elif state == 'replacement_backslash':
                if c == '/':
                    out['replacement'] += '/'
                else:
                    out['replacement'] += '\\' + c
                state = 'replacement'
            elif state == 'flags':
                f = c.lower()
                if f == 'g':
                    out['flags']['global'] = True
                elif f == 'i':
                    out['flags']['insensitive'] = True
                elif f == ';':
                    result.append(out)
                    out = skeleton()
                    hits = skelhits()
                    state = 'start'
                elif f.isdigit():
                    if hits['flags_offset'] == 0:
                        out['flags']['offset'] = int(f)
                        state = 'flags_offset'
                    else:
                        return error(i, 'multiple offset flags not allowed')
                else:
                    return error(i, 'invalid flag')
            elif state == 'flags_offset':
                f = c.lower()
                if f.isdigit():
                    out['flags']['offset'] *= 10
                    out['flags']['offset'] += int(f)
                elif f == 'g':
                    out['flags']['global'] = True
                    state = 'flags'
                elif f == 'i':
                    out['flags']['insensitive'] = True
                    state = 'flags'
                elif f == ';':
                    result.append(out)
                    out = skeleton()
                    hits = skelhits()
                    state = 'start'
                else:
                    return error(i, 'invalid flag')
            else:
                return error(i, 'invalid parser state')
        if state != 'flags' and state != 'flags_offset':
            return error(i, 'invalid parser state at end of expression')
        result.append(out)
        return result
