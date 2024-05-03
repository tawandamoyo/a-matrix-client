import aiohttp
import asyncio
import logging
import math
import os
import re
import sys
import time
import typing
from urllib.parse import quote as urlquote, urljoin, urlparse

from . import error
from . import events
from . import pubsub
from . import schema

{{client module classes}}

# {{client module functions}}

async def check_response(
        resp: aiohttp.ClientResponse,
) -> tuple[int, dict[str, typing.Any]]:
    """Checks whether an HTTP response is an error
    
    If successful, returns the HTTP code and the response body. 
    Raises an exception in case of error
    """

    try: 
        if resp.status < 200 or resp.status >= 400:
            result = await resp.json()
            if "errcode" not in result: 
                raise error.NotMatrixServerError()
            raise error.MatrixError(resp.status, result)
        else:
            return (resp.status, await resp.json())
    except error.MatrixError:
        raise
    except:
        raise error.NotMatrixServerError()   
    
    
async def retry(limit: int, req_func, *args, **kwargs) -> aiohttp.ClientResponse:
    """REtry a request unitl a time limit is reached.
    The request will be retried if a non-Matrix response is received, or if the request was rate limited
    
    Arguments: 
    
    ''limit'': 
        the time limit in ms
    ``req_func``: 
        the function to call to make the request. e.g to make a ``GET`` reequest, this could be a ``session.gt`` where ``session`` is a ``aiohttp.ClientSession```.
    ``*args, **kwargs``:
        the arguments to pass to ``req_fun``. 
    """

    end_time = time.monotonic_ns() + limit * 1_000_000
    backoff = 2
    
    while True:
        resp = await req_func(*args, **kwargs)
        # FIXME: handle no response (aiohttp.ClientConnectionError)
        if resp.status < 400:
            # not an error response, so return 
            return resp
        
        try: 
            # try to parse the error
            result = await resp.json()
        except:
            if time.monotonic_ns() > end_time:
                return resp
            
            await resp.release()
            ## does not look like Matrix serve, so exponential backoff
            ## but if the backofff would take us past our limit, wait until our
            # time limit and make one last attempt
            delay = min(backoff, (end_time - time.monotonic_ns()) / 1_000_000)
            await asyncio.sleep(delay)
            backoff = backoff * 2
            continue
        
        if time.monotonic_ns() > end_time:
            return resp
        elif (
            resp.status == 429 # too many requests
            and "Retry-After" in resp.headers
            and re.match(r"^[\d]+$", resp.headers["Retry-After"])
        ):
            await resp.release()
            delay = int(res.headers["Retry-After"])
            # we are rate limited -- wait for the requested amount
            # in this case, if the delay would take us past our limit, there's 
            # no point in tryin g again because the server says it will still be 
            # rejected, so just return
            
            if time.monotonic_ns() + delay * 1_000_000 > end_time: 
                return resp
            await asyncio.sleep(delay)
            continue
        elif(
            "errcode" in result
            and result["errcode"] == "M_LIMIT_EXCEEDED"
            and type(result.get("retry_after_ms")) == int
        ):
            await resp.release()
            delay_ms = result["retry_after_ms"]
            if time.monotonic_ns() + delay_ms * 1_000_000 > end_time:
                return resp
            await asyncio.sleep(math.ceil(delay_ms / 1_000))
            continue
        else:
            # some other error, so return and let the application deal with it
            return resp

