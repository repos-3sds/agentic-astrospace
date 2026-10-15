import { ApiError, friendlyApiMessage } from './api.service';

describe('friendlyApiMessage', () => {
  it('never shows the raw backend detail on the screen', () => {
    expect(friendlyApiMessage(500, 'Internal Server Error')).not.toContain('Internal Server Error');
    expect(friendlyApiMessage(500, 'Internal Server Error')).toContain('Try again');
    const pydantic = [{ type: 'date_from_datetime_parsing', loc: ['query', 'date'], msg: 'Input should be a valid date' }];
    expect(friendlyApiMessage(422, pydantic)).not.toContain('loc');
    expect(friendlyApiMessage(422, pydantic)).toContain('weren’t valid');
  });

  it('names the problem the user can fix', () => {
    expect(friendlyApiMessage(400, "City 'Mumbaii' not in offline database.")).toContain('place that city');
    expect(friendlyApiMessage(400, "Unknown timezone 'Asia/Nowhere'")).toContain('time zone');
    expect(friendlyApiMessage(400, 'Invalid birth details: hour must be in 0..23')).toContain('birth details');
    const unresolved = 'We couldn’t find “Mumbaii” in IN. Choose the birth place from the search results.';
    expect(friendlyApiMessage(422, unresolved)).toBe(unresolved);
    expect(friendlyApiMessage(404, 'Kundli not found')).not.toContain('Kundli');
    expect(friendlyApiMessage(0, '')).toContain('connection');
    expect(friendlyApiMessage(401, 'Not authenticated')).toContain('sign in');
    expect(friendlyApiMessage(409, 'A profile for yourself already exists.')).toContain('profile for yourself');
  });

  it('keeps the raw detail on the error for diagnostics', () => {
    const error = new ApiError(friendlyApiMessage(500, 'Internal Server Error'), 500, 'Internal Server Error');
    expect(error.message).not.toBe('Internal Server Error');
    expect(error.detail).toBe('Internal Server Error');
    expect(error.status).toBe(500);
    expect(error instanceof Error).toBeTrue();
  });
});
