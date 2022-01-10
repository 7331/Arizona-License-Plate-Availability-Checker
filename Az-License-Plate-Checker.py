#!/usr/bin/env python3.9
import re

from bs4 import BeautifulSoup
from requests import Session

_REQUESTS_TIMEOUT = 10

_PLATE_STATUS_REGEX = re.compile('.+')


def _refresh_cookies(s: Session):
    s.cookies.clear()
    s.get('https://servicearizona.com/plateAvailability', timeout=_REQUESTS_TIMEOUT)
    # e = "session" (starts at 1 and increments on refresh/restart), s = step (starts at 1 on refresh/restart, increments for every request, and is 2 when submitting the POST request).
    s.get('https://servicearizona.com/plateAvailability/plate?execution=e1s1&_eventId=select&plate=1064&screenWidth=1366', timeout=_REQUESTS_TIMEOUT)


def check_plates(plates: list[str], *, log_path: str = 'available.txt'):
    plate_count = len(plates)
    checked_plates: set[str] = set()

    with Session() as s:
        s.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
        _refresh_cookies(s)

        with open(log_path, 'ab') as f:
            for i, plate in enumerate(plates):
                # Even if the plate is a repeat, still output the correct line # to better keep track.
                print(f'\r#{i + 1:,}/{plate_count:,}', end='')

                if plate in checked_plates:
                    continue

                while True:
                    try:
                        r = s.post('https://servicearizona.com/plateAvailability/plate?execution=e1s2', data={'personalization': plate, '_eventId_checkPersonalization': ''}, timeout=_REQUESTS_TIMEOUT)
                        personalization_input = BeautifulSoup(r.content, 'html.parser').select_one('#personalization')

                        # There are too many possible variants to reliably parse explicitly.
                        plate_status = personalization_input.find_next(text=_PLATE_STATUS_REGEX).get_text(strip=True)

                        if plate_status == f'The plate number {plate} is available. To order, click "Order your personalized plate", or try another personalization and search again.':
                            f.write(f'{plate}\n'.encode())
                            # f.flush()
                        elif plate_status != f'Plate {plate} is not available. It is either assigned to a vehicle or is not available due to unacceptable content. Please search again.':
                            # For some strange reason, anything with "ass" in the input results in an empty value.
                            personalization_input_value: str = personalization_input['value']

                            if personalization_input_value != plate:
                                _refresh_cookies(s)
                                continue  # raise ValueError(f'{personalization_input_value} != {plate}')
                            elif plate_status == 'An error occurred during the plate lookup. Plate number is invalid.':
                                print(f'\n{plate}: APPARENTLY BANNED?!\n')
                            elif plate_status not in {
                                'License Plate is invalid.',
                                'The length of the plate text is longer than the plate allows. Please reduce the length.',
                                'A plate personalization is required. Please enter your desired plate text into the "YOUR PERSONALIZATION" field and try again.',
                                'The plate text cannot have spaces at its beginning or end'  # [sic]
                            }:
                                raise ValueError('Unknown plate status: ' + plate_status)

                        checked_plates.add(plate)
                        break
                    except Exception as e:
                        print(f'\n[ERROR] {plate}: {repr(e)}\n')


def main():
    with open('words.txt') as f:
        # Have to iterate twice to get the total count of all plates.
        plates = [line.strip().upper() for line in f]

    check_plates(plates)


if __name__ == '__main__':
    main()
