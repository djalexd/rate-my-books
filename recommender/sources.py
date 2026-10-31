# This file defines various possible sources.
from typing import Any, List
import dropbox

def list_dropbox_folder(
  client: dropbox.Dropbox,
  path: str
) -> List[Any]:

  def start_list_dropbox_folder_internal(the_path):
    response = client.files_list_folder(path = path)
    return response.entries, response.cursor

  def list_dropbox_folder_internal(the_path, cursor):
    if not cursor:
      return []

    response = client.files_list_folder_continue(cursor)
    next_cursor = response.cursor if len(response.entries) > 0 else None
    return response.entries + list_dropbox_folder_internal(the_path, next_cursor)
  
  entries, cursor = start_list_dropbox_folder_internal(path)
  return entries + list_dropbox_folder_internal(path, cursor)

def dropbox_generator(path: str, access_token: str):
  """
    Creates a python generator that yields results from a Dropbox path
  """
  if not access_token:
    raise Exception("Cannot instantiate Dropbox client without an access token")

  dbx = dropbox.Dropbox(access_token)
  for entry in list_dropbox_folder(client=dbx, path=path):
    yield entry