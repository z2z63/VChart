from abc import ABC
from typing import Callable, Iterable
import sys

from vchat.core.interface import CoreInterface
from vchat.model import Contact, ContactTypes

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

class CoreUtilsMixin(CoreInterface, ABC):
    def _contact_iter_helper(self, contact_types: ContactTypes) -> Iterable[Contact]:
        if ContactTypes.CHATROOM in contact_types:
            for contact in self.chatrooms.values():
                yield contact;
        if ContactTypes.USER in contact_types:
            for contact in self.friends.values():
                yield contact;
        if ContactTypes.MP in contact_types:
            for contact in self.mps.values():
                yield contact;
        return
    @override
    def search_contact(self, searcher: Callable[[Contact], bool], contact_types=ContactTypes.ALL) -> list[Contact]:
        result = []
        for contact in self._contact_iter_helper(contact_types):
            if searcher(contact):
                result.append(contact)
        return result
    @override
    def search_friends(self, searcher: Callable[[Contact], bool]) -> list[Contact]:
        return self.search_contact(searcher, ContactTypes.USER)
    @override
    def search_chatrooms(self, searcher: Callable[[Contact], bool]) -> list[Contact]:
        return self.search_contact(searcher, ContactTypes.CHATROOM)
    @override
    def search_friends_by_nickname(self, name: str) -> list[Contact]:
        return self.search_contact(lambda contact: name in contact.nickname, ContactTypes.USER)
    @override
    def search_chatrooms_by_nickname(self, name: str) -> list[Contact]:
        return self.search_contact(lambda contact: name in contact.nickname, ContactTypes.CHATROOM)