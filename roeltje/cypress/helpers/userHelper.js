import strings from './stringHelper';

const userHelper = () => {
    const newUser = ({user, randomString}) => {
    randomString = randomString || strings.random(4);

      return {
        ...user,
        name: `${user.name} ${randomString}`,
        email: user.email.replace('{RANDOM_STRING}', randomString),
        organization: `${user.organization} ${randomString}`,
      }
    };

    return {
        newUser
    }
};

export default userHelper()
