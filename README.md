# I'm Coming To TYA Bot
![Current version](https://img.shields.io/badge/version-v1.2-blue)
<a href="https://github.com/python-telegram-bot/python-telegram-bot">![Python Telegram Bot version](https://img.shields.io/badge/python--telegram--bot-v13.7-teal)</a>
![Supported Python version](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-teal?logo=python&logoColor=yellow)
![MIT License](https://img.shields.io/badge/license-MIT-orange)
<a href="https://t.me/imcomingtotyabot">![Bot Username](https://img.shields.io/badge/username-@imcomingtotyabot-blue?logo=telegram)</a>

_Adapted from [countmeinbot](https://github.com/whipermr5/countmeinbot) by [whipermr5](https://github.com/whipermr5/)_

---

This is a private project to build a Telegram bot which helps to build polls.
What's unique about this bot is that it allows users to **write comments** on their chosen option!

While this may be a private project, it is **open-source**. 
Feel free to use my code, make changes, and run on your own server 😉.

---

<table>
  <tbody>
    <tr align="left">
      <th><h3>🎉 What's New?</h3></th>
    </tr>
    <tr>
      <td>
        <b>Groups</b>
        <ul>
          <li>You can now create groups* to share your created polls! 😁
            <ul>
              <li><i>Only if permission is given to you by the <b>bot admin</b></i></li>
            </ul>
          </li>
          <li>Invite group members to join your group</li>
          <li>Share and view created polls from other group members</li>
        </ul>
        <b>Lists</b>
        <ul>
          <li>You can now create a new kind of poll - Lists! 😁</li>
          <li>Lists are like manual polls where you first create a list of names that can be placed in the options</li>
          <li>Add the names to each option in the list</li>
          <li><b>Great for attendance taking or organising people into groups!</b> 😉</li>
        </ul>
        <b>Miscellaneous</b>
        <ul>
          <li>You can now add descriptions to polls!</li>
          <li>Use <code>/gpolls</code> and <code>/glists</code> to now view all your group polls and lists!</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>

---

## Features

### Polls
- 🆕 You can now add descriptions to polls!
- Build a standard poll with options where users can vote their names
- Toggle between single or multiple votes allowed for each user
- Toggle whether a comment is required for each option in the poll
- Users may leave a comment for an option they selected
  - If comment is required, users are forced to enter a comment or their vote will not be registered

### Lists 🆕
- Build a manual poll with options and pre-determined choices
- Set of options and choices must be made beforehand
- Insert each choice in one or multiple options, depending on the settings
- **Great for attendance taking or organising people into groups!** 👏

### Groups 🆕
<table>
  <tr>
    <td><h3>⚠</h3></td>
    <td>
      Only users with permission given by the <b>bot admin</b> can create groups. 
      However, you can still join groups via group invites 😄.
    </td>
  </tr>
</table>

- Create a group and invite members to share and view each other's polls
- Group owner can remove members and group polls from the group
- Create password to secure the group

---

## Bot Usage

### Commands
<table>
  <tr>
    <td><h3>ℹ</h3></td>
    <td>
      As different users have different access privileges, the default Telegram command
      suggestions cannot be used 😭.
      <br><br>
      As a compromise, <a href="#inline-queries">inline queries</a> are used to 
      display the available commands to you. 
      <br><br>
      Alternatively, you may use the <code>/help</code> command for the bot to display 
      the list of commands available to you and their functions.
    </td>
  </tr>
</table>

Bot commands always begin with a `/` character.
Essentially it starts a conversation with the bot and triggers it to carry out a
particular action.
  
Below is a list of bot commands as of this version.

| Command         | Description                                             | Permission Type |
|:----------------|:--------------------------------------------------------|:---------------:|
| `/start`        | Views the bot's welcome message                         |      None       |
| `/poll [title]` | Builds a new poll with an optional title                |       Bot       |
| `/polls`        | Views all the polls you have built                      |       Bot       |
| `/list [title]` | Builds a new list with an optional title                |       Bot       |
| `/lists`        | Views all the lists you have built                      |       Bot       |
| `/group [name]` | Creates a new group with an optional name               |     Leader      |
| `/groups`       | Views all the groups you are in                         |       Bot       |
| `/gpolls`       | Views all the group polls in all your groups            |       Bot       |
| `/glists`       | Views all the group lists in all your groups            |       Bot       |
| `/invite`       | Sends an invite link to your friends to join your group |       Bot       |
| `/help`         | Views the help message to show available commands       |      None       |

<table>
  <tr>
    <td><h3>ℹ</h3></td>
    <td>
      If you try to use a bot command that is invalid or that you do not have access to, 
      the bot will very intelligently show you the help message instead 😆.
    </td>
  </tr>
</table>

### Inline Queries
Inline queries to the bot begin with the bot's username, i.e. `@imcomingtotyabot`. The 
best thing about inline queries is its auto-complete functionality 😁.
  
Below is a list of inline queries processed by the bot as of this version.

| Inline Query       | Description                                                                               | Permission Type |
|:-------------------|:------------------------------------------------------------------------------------------|:---------------:|
| `/`                | Views all available bot commands to you                                                   |      None       |
| `/access <code>`   | Accesses the bot's standard features via the invite code sent to you by the **bot admin** |      None       |
| `/start`           | Views the bot's welcome message                                                           |      None       |
| `/poll`            | Builds a new poll                                                                         |       Bot       |
| `/poll <title>`    | Builds a new poll with the given title                                                    |       Bot       |
| `/polls`           | Views all the polls you have built                                                        |       Bot       |
| `/polls [filter]`  | Shows polls filtered by title for you to choose to view                                   |       Bot       |
| `/lists [filter]`  | Shows lists filtered by title for you to choose to view                                   |       Bot       |
| `/list`            | Builds a new list                                                                         |       Bot       |
| `/list <title>`    | Builds a new list with the given title                                                    |       Bot       |
| `/lists`           | Views all the lists you have built                                                        |       Bot       |
| `/lists [filter]`  | Shows lists filtered by title for you to choose to view                                   |       Bot       |
| `/group`           | Creates a new group                                                                       |     Leader      |
| `/group <name>`    | Creates a new group with the given name                                                   |     Leader      |
| `/groups`          | Views all the groups you are in                                                           |       Bot       |
| `/groups [filter]` | Shows groups filtered by name for you to choose to view                                   |       Bot       |
| `/gpolls`          | Views all your group polls                                                                |       Bot       |
| `/gpolls [filter]` | Shows group polls filtered by name for you to choose to view                              |       Bot       |
| `/glists`          | Views all your group lists                                                                |       Bot       |
| `/glists [filter]` | Shows group lists filtered by name for you to choose to view                              |       Bot       |
| `/invite`          | Sends an invite link to your friends to join your group                                   |       Bot       |
| `/invite [filter]` | Shows groups filtered by name for you to choose to send an invite link for                |       Bot       |
| `/join <code>`     | Joins a group via the invite code sent by an existing group member                        |      None       |
| `/help`            | Views the help message to show available commands                                         |      None       |
| `[filter]`         | Shows all your polls and lists filtered by title for you to choose to publish             |       Bot       |

<table>
  <tr>
    <td><h3>ℹ</h3></td>
    <td>
      Inline queries to the bot will automatically filter out the options that are not
      available to you.
    </td>
  </tr>
</table>

---

## Upcoming Features
- 🔴 Enable users to create custom templates to build a poll faster!
- 🟡 Editing of fields like titles and descriptions even after poll/list has been created
- 🟡 Pagination of polls/lists with many options for better UI
- 🟢 Add deadlines to polls (users can no longer vote in the poll)
- 🟢 New kind of poll - feedback?

---

*Feel free to give any requests for new features or report any bugs* 🕷 *to the 
**bot admins**!* 
*Your feedback is very much appreciated!* 😊
