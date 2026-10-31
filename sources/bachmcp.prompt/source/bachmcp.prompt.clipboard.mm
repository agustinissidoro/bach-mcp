// bachmcp.prompt.clipboard.mm — the system clipboard (macOS), as UTF-8.

#import <AppKit/AppKit.h>
#include <string>

std::string prompt_clipboard_get()
{
    @autoreleasepool {
        NSString *s = [[NSPasteboard generalPasteboard] stringForType:NSPasteboardTypeString];
        return s ? std::string([s UTF8String]) : std::string();
    }
}

void prompt_clipboard_set(const std::string &text)
{
    @autoreleasepool {
        NSPasteboard *pb = [NSPasteboard generalPasteboard];
        [pb clearContents];
        [pb setString:[NSString stringWithUTF8String:text.c_str()] forType:NSPasteboardTypeString];
    }
}
