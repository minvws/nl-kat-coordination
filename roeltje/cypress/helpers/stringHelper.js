const stringHelper = () => {
  const random = (length) => Math.random().toString(36).replace(/[^a-z]+/g, '').substr(0, length);

  const split = (splittable, separator = ',') => {
    return splittable.split(separator)
            .map(v => v.trim())
            .filter(v => v.length > 0);
  };

  // formattin date easy-mode
  const inputDate = date => new Date(date).toJSON().split("T")[0];

  const dateToday = new Date();
  const dateYesterday = new Date().setDate(dateToday.getDate() - 1);
  const dateLastWeek = new Date().setDate(dateToday.getDate() - 7);
  const dateLastYear = new Date().setYear(dateToday.getFullYear() - 1);

  const today = inputDate(dateToday);
  const yesterday = inputDate(dateYesterday);
  const lastWeek = inputDate(dateLastWeek);
  const lastYear  = inputDate(dateLastYear);

  return {
    random,
    split,
    today,
    yesterday,
    lastWeek,
    lastYear,
  };
};

export default stringHelper();
